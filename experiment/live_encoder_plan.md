# Live H.264 encoder integration (in progress)

## Architecture

```
uvc_stream (patched + LD_PRELOAD shim)
  |  camera MJPG frame (captured by uvc_stream)
  v
shim: write frame to /tmp/mjpg_in, read H.264 from /tmp/h264_out
  ^
  |  ffmpeg -f mjpeg -i pipe:0 -c:v libx264 -f h264 pipe:1
  |
  +-- separate encoder process (MIPS static binary)

shim: pad H.264 access unit to the caller's requested size with SEI NALs,
      substitute into Creality's frame buffer
  -> AvEncode_from_camera -> ring buffer -> WebRTC
```

## Why padding with SEI NALs

`upgrade_video_buf` passes the original camera buffer size `n` to
`AvEncode_from_camera`. The injected H.264 must be exactly `n` bytes. Appending
valid SEI NAL units (type 6) of arbitrary length lets us pad cleanly without
breaking decoders.

## Build status

- OpenWrt 19.07 mt76x8 SDK available at `/tmp/opencode/openwrt-sdk-...`.
- `ffmpeg` package enabled in `.config` (`CONFIG_PACKAGE_ffmpeg=m`).
- Static linkage is required: the box uses uClibc 0.9.33.2, while the SDK
  defaults to musl. Either force `-static` in the package LDFLAGS or use a
  uClibc toolchain.
- The shim itself is already uClibc-compatible (built `-nostdlib`).

## Test result so far

File-based injection reached: no crash, SPS/PPS parsed, WebRTC connected,
app spinner. Remaining: NAL-boundary alignment and a live encoder.

## Next steps

1. Finish static ffmpeg build for MIPS.
2. Extend shim: MJPG -> FIFO -> ffmpeg -> H.264 FIFO, SEI pad to `n`.
3. Test with the real camera; verify app shows video.
4. Only then consider baking the patched binary + shim + encoder into a new
   firmware image (using `build_patched_firmware.py` as the base).

## Update: raw YUYV is not viable

Tested `-m yuv422` at 640x480 and 320x240: the driver reports
`V4L2_PIX_FMT_YUYV` but delivers **no frames** (`select Timeout` continuously).
Only MJPG produces frames on this USB 2.0 hub.

A static MIPS x264 CLI was built successfully with the OpenWrt SDK
(`--host=mipsel-openwrt-linux --enable-static --disable-asm`), and it runs on
the box. But x264 cannot consume MJPG frames.

**Remaining missing piece:** a static MIPS JPEG decoder (libjpeg-turbo) plus a
small bridge that decodes the camera's MJPG frames to YUV and pipes them into
x264. The shim then pads the resulting H.264 with Filler Data NALs (type 12) to
the exact camera buffer size before handing it to `AvEncode_from_camera`.

ffmpeg was attempted but the 19.07 SDK build fails on host autotools (`AM_ICONV`)
and missing zlib; building libjpeg-turbo + x264 directly is the cleaner route.
