# Creality Print Hub WB01 — camera compatibility firmware builder

Tools to patch a **Creality WiFi / Print Hub box** firmware (MT7628, Linux 2.6.36,
version V3.04b06) so the camera launch path uses MJPEG instead of H.264.

## Status: VERIFIED on hardware

Built and flashed on a V3.04b06 box; it boots normally and every patched file is
present with the expected checksum. `prt_com` and other user modifications are
preserved. Keep your original firmware archive for recovery.

## Why

The box's `uvc_stream` WebRTC sender is H.264-only (`send_h264_thread`,
`h264_packetizer_*`, no software encoder), but the built-in `uvcvideo` driver in
kernel 2.6.36 only supports UVC `UNCOMPRESSED`, `MJPEG` and `DV` formats — no
UVC H.264. A modern UVC camera that advertises H.264 (e.g. Logitech BRIO) is
therefore never usable: capture fails, and forcing MJPEG later crashes the
sender. These patches normalize the launch command to
`-m MJPG -r 640x480 -f 15` in every launcher.

This does **not** add H.264 support; it only makes the box consistently request
a format its own kernel can capture. A plain MJPEG webcam is still required for
a usable video feed.

## What is patched

- `home/app_daemon.sh`     — cron launcher normalization
- `etc_ro/rcS`             — boot launcher normalization
- `sbin/video.sh`          — USB hotplug launcher (source of bad H.264 commands)
- `sbin/video_daemon.sh`   — LED-daemon launcher normalization
- `bin/uvc_stream`         — compatibility wrapper
- `usr/bin/uvc_stream`     — original streamer, wrapper target

Everything else, including `home/prt_com`, is left untouched.

## Build

You need your own copy of the Creality firmware update archive
(`cxsw_update.tar.bz2`, obtained from Creality Cloud / your own box). This
repository does **not** redistribute it.

```sh
python3 build_patched_firmware.py /path/to/cxsw_update.tar.bz2 ./cxsw_update_patched.tar.bz2
```

The script unpacks the uImage, patches the files above, rebuilds the initramfs,
recomputes both uImage CRCs and the archive `_md5_`, and emits an SD-card-ready
archive.

### Important: initramfs size

The kernel has a **built-in initramfs with link-time start/end symbols**. If the
recompressed initramfs is even slightly *larger* than the original, the kernel
truncates it and fails to boot (box shows a solid amber light and gets no IP).
The builder uses the default xz preset and refuses to emit an image if the new
stream is larger than the original. Do not force a smaller-dictionary preset.

### Flashing

Put the archive at the SD card root named `cxsw_update.tar.bz2` and let the
box's `/sbin/upgrade.sh` install it, or run `install.sh` directly with an
**explicit directory**:

```sh
/tmp/install.sh manual /media/mmcblk0p1
```

Pass a non-empty first argument: an empty `""` can be dropped by the shell,
making `install.sh` fall back to the wrong directory (it will then read a stock
`root_uImage` from the SD card instead of your patched one).

### Recovery

If the box stops responding, use Creality's documented unbrick method: put the
**original** `root_uImage` alone on a FAT32 USB drive or SD card, power the box
off, insert it, and power on. The SD card must contain **only** `root_uImage` —
any other files make the recovery fail.

## License

Scripts are provided as-is. Firmware binaries are Creality property and are not
included.
