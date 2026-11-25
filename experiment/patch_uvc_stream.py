#!/usr/bin/env python3
"""Patch a stock uvc_stream binary for H.264 injection experiments.

Two 4-byte patches:
  1. upgrade_video_buf @ 0x434af8: beq -> j 0x434b1c
     (force AvEncode_from_camera to run regardless of pixel format)
  2. upgrade_video_buf @ 0x434b54: jal FUN_00434b84 -> nop
     (skip recording jobs that crash with injected data)
"""
import struct, sys

TEXT_VADDR, TEXT_OFFSET = 0x431790, 0x31790

def patch_file_offset(vaddr):
    return TEXT_OFFSET + (vaddr - TEXT_VADDR)

data = bytearray(open(sys.argv[1], 'rb').read())
o1 = patch_file_offset(0x434af8)
data[o1:o1+4] = struct.pack('<I', 0x08000000 | (0x434b1c >> 2))
o2 = patch_file_offset(0x434b54)
data[o2:o2+4] = b'\x00\x00\x00\x00'
open(sys.argv[2], 'wb').write(data)
print('patched ->', sys.argv[2])
