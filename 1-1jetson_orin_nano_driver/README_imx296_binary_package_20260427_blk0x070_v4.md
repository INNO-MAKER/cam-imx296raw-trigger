# IMX296 Binary Driver Package — Usage

**Package:** `imx296_binary_package_20260427_blk0x070_v4.tar.gz`

## Contents

```
binary/
  imx296.ko                                                 # kernel module (5.15.148-tegra)
  tegra234-p3767-camera-p3768-imx296-imx296.dtbo            # CSI0 + CSI1 = imx296 (color) + imx296 (color)
  tegra234-p3767-camera-p3768-imx219-imx296.dtbo            # CSI0 + CSI1 = imx219          + imx296 (color)
  tegra234-p3767-camera-p3768-imx477-imx296.dtbo            # CSI0 + CSI1 = imx477          + imx296 (color)
scripts/
  install_binary.sh / install_binary_EN.sh                  # installer (zh / en)
  camera_control.sh                                         # mono preview helper
  camera_control_color.sh                                   # color preview helper
  adjust_brightness.sh                                      # brightness test
```

## Install

```bash
tar -xzf imx296_binary_package_20260427_blk0x070_v4.tar.gz -C ~/imx296_v4
cd ~/imx296_v4/scripts
chmod +x install_binary.sh
./install_binary.sh
```

The installer copies `imx296.ko` to `/lib/modules/$(uname -r)/kernel/drivers/media/i2c/`, copies the `.dtbo` files to `/boot/`, and runs `depmod -a`.

## Configure CSI overlay

Choose which DTBO is loaded at boot using NVIDIA's Jetson-IO tool:

```bash
sudo /opt/nvidia/jetson-io/jetson-io.py
```

In the menu select:

1. **Configure Jetson 24pin CSI Connector**
2. **Configure for compatible hardware**
3. Pick the overlay matching your camera setup, e.g.:
   - `Camera IMX296 Dual` — two IMX296 color sensors
   - `Camera IMX219 + IMX296` — IMX219 on CSI0, IMX296 on CSI1
   - `Camera IMX477 + IMX296` — IMX477 on CSI0, IMX296 on CSI1
4. **Save pin changes** → **Save and reboot to reconfigure pins**

The tool patches `/boot/extlinux/extlinux.conf` with the right `OVERLAYS` line and reboots.

## Verify

```bash
lsmod | grep imx296
dmesg | grep imx296

# Recommended starting values (matches adjust_brightness.sh test 4: indoor / normal)
gst-launch-1.0 nvarguscamerasrc num-buffers=30 \
    gainrange="4 4" exposuretimerange="200000 200000" \
    ! 'video/x-raw(memory:NVMM),width=1456,height=1088' \
    ! nvvidconv ! xvimagesink
```

Supported ranges:

| Control | Min | Max | Unit |
|---|---|---|---|
| `gainrange`         | 1     | 16        | linear multiplier (≈ 0 … 24 dB) |
| `exposuretimerange` | 1000  | 1000000   | nanoseconds (1 µs … 1 ms)       |
| framerate           | ~0.06 | ~60.4     | fps                             |

Brightness presets in `scripts/adjust_brightness.sh`:

| Preset | gain | exposure (ns) | scene            |
|---|---|---|---|
| 1 | 1 | 10 000  | very dark / reference |
| 2 | 1 | 50 000  | bright outdoor        |
| 3 | 2 | 100 000 | normal                |
| 4 | 4 | 200 000 | **indoor (recommended start)** |
| 5 | 8 | 500 000 | low light             |
