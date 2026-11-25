#!/usr/bin/env python3
"""Build a camera-compatibility patched firmware image for the Creality WB01 box.

Usage:
    python3 build_patched_firmware.py INPUT.tar.bz2 OUTPUT.tar.bz2

INPUT must be your own Creality firmware update archive (contains root_uImage,
bImage, install.sh, ver, _md5_, _bmd5_, rw_dir/). No firmware binaries are
shipped with this repository.
"""
import hashlib, os, shutil, struct, subprocess, sys, tarfile, tempfile, zlib

FIX = r'''      cmdline=`echo "$cmdline" | sed -e 's/-m [Hh]264/-m MJPG/g' -e 's/-r 1920x1080/-r 640x480/g' -e 's/-f 30/-f 15/g'`'''
WRAPPER = r'''#!/bin/sh
# Compatibility wrapper: this hub's kernel cannot stream H.264.
# Keep the binary name "uvc_stream" so the daemon's kill logic still matches.
args=""
for a in "$@"; do
  case "$a" in
    /dev/video1) exit 0 ;;
    h264|H264) a="MJPG" ;;
    1920x1080) a="640x480" ;;
    30) a="15" ;;
  esac
  args="$args '$a'"
done
eval "exec /usr/bin/uvc_stream $args"
'''

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)

def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()

def insert_after(path, marker, line):
    data = open(path, encoding='utf-8').read()
    if line in data:
        return
    lines, out, done = data.split('\n'), [], False
    for l in lines:
        out.append(l)
        if marker in l and not done:
            out.append(line)
            done = True
    if not done:
        raise RuntimeError(f'marker not found: {marker} in {path}')
    open(path, 'w', encoding='utf-8').write('\n'.join(out))

def unpack_uimage(path, work):
    raw = open(path, 'rb').read()
    magic, hcrc, ts, size, load, ep, dcrc = struct.unpack('>7I', raw[:28])
    if magic != 0x27051956:
        raise RuntimeError('not a uImage')
    comp = raw[64:]
    if zlib.crc32(comp) & 0xffffffff != dcrc:
        raise RuntimeError('uImage data CRC mismatch')
    lzma_path = os.path.join(work, 'payload.lzma')
    open(lzma_path, 'wb').write(comp)
    payload = run(['xz', '--format=lzma', '-dc', lzma_path],
                  stdout=subprocess.PIPE).stdout
    return payload, load, ep, raw[28:32]

def find_xz_stream(payload):
    """Find the real xz-compressed initramfs (kernel text contains false magic)."""
    candidates = []
    pos = 0x100000
    while True:
        pos = payload.find(b'\xfd7zXZ\x00', pos)
        if pos < 0:
            break
        candidates.append(pos)
        pos += 1
    footer = payload.rfind(b'YZ')
    if footer < 0:
        raise RuntimeError('xz footer not found')
    for start in candidates:
        if footer <= start:
            continue
        end = footer + 2
        try:
            r = subprocess.run(['xz', '-t'], input=payload[start:end],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if r.returncode == 0:
                return start, end
        except subprocess.CalledProcessError:
            continue
    raise RuntimeError('no valid xz initramfs stream found')

def patch_rootfs(root):
    insert_after(os.path.join(root, 'home/app_daemon.sh'), 'echo cmdline is', FIX)
    insert_after(os.path.join(root, 'etc_ro/rcS'), 'echo cmdline is', FIX)
    insert_after(os.path.join(root, 'sbin/video_daemon.sh'), 'echo cmdline is', FIX)
    p = os.path.join(root, 'sbin/video.sh')
    s = open(p, encoding='utf-8').read()
    s = s.replace('-f 30 -r 1920x1080 -m h264', '-f 15 -r 640x480 -m MJPG')
    open(p, 'w', encoding='utf-8').write(s)
    stock = os.path.join(root, 'bin/uvc_stream')
    os.makedirs(os.path.join(root, 'usr/bin'), exist_ok=True)
    shutil.copy2(stock, os.path.join(root, 'usr/bin/uvc_stream'))
    open(stock, 'w', encoding='utf-8').write(WRAPPER)
    os.chmod(stock, 0o755)

def main(src, dst):
    work = tempfile.mkdtemp(prefix='wb01-fw-')
    try:
        stage = os.path.join(work, 'stage')
        os.makedirs(stage)
        with tarfile.open(src, 'r:bz2') as t:
            t.extractall(stage)
        payload, load, ep, meta = unpack_uimage(os.path.join(stage, 'root_uImage'), work)
        xstart, xend = find_xz_stream(payload)
        cpio_path = os.path.join(work, 'rootfs.cpio')
        open(os.path.join(work, 'rootfs.xz'), 'wb').write(payload[xstart:xend])
        cpio_data = run(['xz', '-dc', os.path.join(work, 'rootfs.xz')],
                        stdout=subprocess.PIPE).stdout
        open(cpio_path, 'wb').write(cpio_data)
        root = os.path.join(work, 'rootfs')
        os.makedirs(root)
        run(['cpio', '-idmu', '--no-absolute-filenames', '--no-preserve-owner',
             '--quiet'], cwd=root, input=cpio_data)
        patch_rootfs(root)

        new_cpio = os.path.join(work, 'new.cpio')
        with open(new_cpio, 'wb') as out:
            run(['bash', '-c', f'cd {root} && find . -print0 | cpio -o -H newc --owner=0:0 --null'],
                stdout=out)
        new_xz_path = os.path.join(work, 'new.xz')
        with open(new_xz_path, 'wb') as out:
            run(['xz', '--check=crc32', '-c', new_cpio], stdout=out)
        new_xz = open(new_xz_path, 'rb').read()
        if len(new_xz) > xend - xstart:
            raise RuntimeError('recompressed initramfs is larger than the original; '
                               'the kernel may not boot — try a different xz preset')

        new_payload = bytearray(payload)
        new_payload[xstart:xend] = new_xz + b'\0' * (xend - xstart - len(new_xz))
        np_path = os.path.join(work, 'payload_new.bin')
        open(np_path, 'wb').write(new_payload)

        comp_path = os.path.join(work, 'payload_new.lzma')
        with open(comp_path, 'wb') as out:
            run(['xz', '--format=lzma', '--lzma1=dict=32MiB', '-c', np_path], stdout=out)
        comp = bytearray(open(comp_path, 'rb').read())
        comp[5:13] = struct.pack('<Q', len(new_payload))
        open(comp_path, 'wb').write(comp)
        if run(['xz', '--format=lzma', '-dc', comp_path],
               stdout=subprocess.PIPE).stdout != bytes(new_payload):
            raise RuntimeError('LZMA round-trip failed')

        header = bytearray(64)
        struct.pack_into('>7I', header, 0, 0x27051956, 0, ts_from(src), len(comp),
                         load, ep, zlib.crc32(comp) & 0xffffffff)
        header[28:32] = meta
        header[32:64] = b'Linux Kernel Image'.ljust(32, b'\0')
        struct.pack_into('>I', header, 4, zlib.crc32(header) & 0xffffffff)
        new_image = bytes(header) + bytes(comp)
        open(os.path.join(stage, 'root_uImage'), 'wb').write(new_image)
        open(os.path.join(stage, '_md5_'), 'w').write(md5(os.path.join(stage, 'root_uImage')))
        with tarfile.open(dst, 'w:bz2') as t:
            for name in sorted(os.listdir(stage)):
                t.add(os.path.join(stage, name), arcname=name)
        print('wrote', dst, 'image md5', md5(os.path.join(stage, 'root_uImage')))
    finally:
        shutil.rmtree(work, ignore_errors=True)

def ts_from(src):
    with tarfile.open(src, 'r:bz2') as t:
        raw = t.extractfile('root_uImage').read(28)
    return struct.unpack('>7I', raw)[2]

if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
