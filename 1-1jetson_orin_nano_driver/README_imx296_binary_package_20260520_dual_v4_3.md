# IMX296 Binary Driver Package - Dual Camera v4.3

Package: `imx296_binary_package_20260520_dual_v4_3.tar.gz`

Target: Jetson Orin Nano/NX, L4T r36.4.4, kernel `5.15.148-tegra`

## Contents

```text
binary/
  imx296.ko
  tegra234-p3767-camera-p3768-imx296-imx296.dtbo
scripts/
  install_binary.sh
  camera_control_color.sh
  camera_control_mono.sh
  adjust_brightness.sh
```

This package intentionally includes only the verified dual IMX296 overlay. Single-CAM0 overlays are not included because CAM0-only testing showed the routing is board-specific and easy to misuse.

Other sensor combinations, such as IMX219 + IMX296 or IMX477 + IMX296, require their own DTS/DTBO files and are not included in this release.
Please contact us if you need support for other sensor combinations.

Both cameras were verified individually and simultaneously with V4L2 and Argus/GStreamer.

## Install

```bash
tar -xzf imx296_binary_package_20260520_dual_v4_3.tar.gz
cd imx296_binary_package_20260520_dual_v4_3/scripts
chmod +x install_binary.sh
./install_binary.sh
```

The installer copies `imx296.ko` to `/lib/modules/$(uname -r)/kernel/drivers/media/i2c/`, copies the DTBO to `/boot/`, and runs `depmod -a`.

The installer also removes stale `/boot/*imx296*.dtbo` files except the verified dual overlay:

```text
/boot/tegra234-p3767-camera-p3768-imx296-imx296.dtbo
```

This prevents selecting old single-camera or test overlays by mistake.

The installer does not remove non-IMX296 camera overlays.

## Select Overlay

Use Jetson-IO:

```bash
sudo /opt/nvidia/jetson-io/jetson-io.py
```

Select the following overlay display name, save, and reboot:

```text
Camera IMX296-C and IMX296-C
```

Alternatively, make sure `/boot/extlinux/extlinux.conf` contains:

```text
OVERLAYS /boot/tegra234-p3767-camera-p3768-imx296-imx296.dtbo
```

Then reboot:

```bash
sudo reboot
```

## Verify

```bash
lsmod | grep imx296
ls -l /dev/video*
v4l2-ctl -d /dev/video0 --list-formats-ext
v4l2-ctl -d /dev/video1 --list-formats-ext
```

Single-camera preview:

```bash
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! \
  'video/x-raw(memory:NVMM),width=1456,height=1088,framerate=30/1' ! \
  nvvidconv ! xvimagesink sync=false
```

Dual-camera preview must be run in one process/pipeline:

```bash
gst-launch-1.0 -e \
  nvarguscamerasrc sensor-id=0 ! 'video/x-raw(memory:NVMM),width=1456,height=1088,framerate=30/1' ! queue ! nvvidconv ! xvimagesink sync=false \
  nvarguscamerasrc sensor-id=1 ! 'video/x-raw(memory:NVMM),width=1456,height=1088,framerate=30/1' ! queue ! nvvidconv ! xvimagesink sync=false
```

Do not use two independent Argus applications for simultaneous preview; Argus can report `AlreadyAllocated` if the camera provider is opened from separate processes.

## Helper Scripts

For color IMX296 preview/control:

```bash
cd scripts
./camera_control_color.sh
```

For mono IMX296 preview/control:

```bash
cd scripts
./camera_control_mono.sh
```
