#!/usr/bin/env python3
"""Repackage an Annex-B H.264 file into fixed-size blocks, each holding a
complete access unit (SPS+PPS+one frame), so the LD_PRELOAD shim can feed one
whole frame per uvc_stream memcpy call."""
import sys

BLOCK = 36000
data = open(sys.argv[1], 'rb').read()

# split into NAL units with 4-byte start codes
nals = []
pos = 0
while True:
    i = data.find(b'\x00\x00\x00\x01', pos)
    if i < 0:
        break
    j = data.find(b'\x00\x00\x00\x01', i + 4)
    if j < 0:
        j = len(data)
    nals.append(data[i:j])
    pos = j

sps = [n for n in nals if len(n) > 4 and (n[4] & 0x1f) == 7]
pps = [n for n in nals if len(n) > 4 and (n[4] & 0x1f) == 8]
frames = [n for n in nals if len(n) > 4 and (n[4] & 0x1f) in (1, 5)]
print('nals', len(nals), 'sps', len(sps), 'pps', len(pps), 'frames', len(frames))

if not sps or not pps or not frames:
    raise SystemExit('not enough NALs')

out = bytearray()
for f in frames:
    au = sps[0] + pps[0] + f
    if len(au) > BLOCK:
        continue
    out += au + b'\x00' * (BLOCK - len(au))
open(sys.argv[2], 'wb').write(out)
print('wrote', sys.argv[2], len(out), 'bytes,', len(out) // BLOCK, 'blocks')
