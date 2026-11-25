# Reverse-engineering notes: why the camera stream fails

Binary: `/usr/bin/uvc_stream`, MIPS32r2 little-endian, uClibc, stripped but with
dynamic symbols. Build path embedded in the binary:
`/usr/sank/creality_gitlab/wb-01-cgs/wb-01/software/MTK_APSoC_SDK/source/user/uvc_stream/libsdwrite/`

## Pipeline

```
camera (V4L2)
  -> upgrade_video_buf(0x434538)
       memcpy(frame, camera_buf, size)
       if fourcc == 0x34363248 (H264) or 0x35363248 (H265):
           AvEncode_from_camera(0x4324f0) -> Rbuffer_sendFrameToBuff(0x4448f4)
  -> send_h264_thread(0x4545d8)
       rtc_getStream_(0x433ddc) -> Rbuffer_getOneFrame(0x445efc)
       h264_packetizer_send -> WebRTC
```

## Root cause

`AvEncode_from_camera` is only called for H264/H265 fourcc. With MJPG the block
is skipped, the ring buffer stays empty, and `send_h264_thread` crashes with
SIGSEGV when it dereferences the missing buffer (`brec:0` is a playback tick,
not a buffer count).

Kernel 2.6.36 uvcvideo supports only UVC UNCOMPRESSED / MJPEG / DV formats —
no UVC H.264 — so a modern webcam that advertises H.264 (e.g. Logitech BRIO)
can never supply H.264 NAL units through the stock path.

## Experiment (see tools/ and experiment/)

- `experiment/patch_uvc_stream.py` forces the H264 branch and skips recording jobs.
- `experiment/h264feed.c` is an LD_PRELOAD shim:
  - hooks memcpy at Creality's exact frame-buffer pointer (`0x8f6158`)
  - calls `rtspsrv_init` (0x43435c) once to initialize the ring buffer
  - injects H.264 Annex-B data from `/tmp/h264feed`
- `tools/make_blocks.py` repackages an H.264 file into fixed-size access-unit
  blocks (work in progress: alignment with arbitrary camera buffer sizes).

Result: no crash, H.264 SPS/PPS parsed by Creality's own code, WebRTC connects,
app shows a spinner instead of "stream disconnected". Remaining work: feed
properly framed **live** H.264 (cross-compiled encoder) instead of a file.

## Status

The production firmware builder (`build_patched_firmware.py`) remains the
verified, safe change set. The experiment is not shipped in the image.
