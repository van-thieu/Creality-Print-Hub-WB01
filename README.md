# Creality Print Hub WB01 — camera compatibility firmware builder

Tools to patch a **Creality WiFi / Print Hub box** firmware (MT7628, Linux 2.6.36,
version V3.04b06) so the camera launch path uses MJPEG instead of H.264.

## Why

The box's `uvc_stream` WebRTC sender is H.264-only (`send_h264_thread`,
`h264_packetizer_*`, no software encoder), but the built-in `uvcvideo` driver in
kernel 2.6.36 only supports UVC `UNCOMPRESSED`, `MJPEG` and `DV` formats — no
UVC H.264. A modern UVC camera that advertises H.264 (e.g. Logitech BRIO) is
therefore never usable: capture fails, and forcing MJPEG later crashes the
sender. These patches normalize the launch command to
`-m MJPG -r 640x480 -f 15` in every launcher.

This does **not** add H.264 support; it only makes the box consistently request
a format its own kernel can capture. A plain MJPEG webcam is still required.

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
archive. Name it `cxsw_update.tar.bz2` on the SD card root and let the box's
`/sbin/upgrade.sh` install it.

## Status

EXPERIMENTAL — verify on your own hardware. Keep your original firmware archive
for recovery. The box can be restored with Creality's documented unbrick method
(place `root_uImage` on a USB drive and power on).

## License

Scripts are provided as-is. Firmware binaries are Creality property and are not
included.
