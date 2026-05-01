# CAM-IMX296RAW-TRIGGER Camera Module

The **CAM-IMX296RAW-TRIGGER** is an industrial-grade camera module featuring the **Sony IMX296** global shutter CMOS sensor. It is designed for high-speed motion capture, automation, and machine vision applications where rolling shutter distortion must be eliminated.

This module is fully compatible with Raspberry Pi (3, 4, 5) and NVIDIA Jetson Orin Nano, supporting advanced features like hardware trigger and strobe synchronization.

---

## Key Features

*   **Sony IMX296 Global Shutter Sensor**: 1.58 MP (1456 x 1088) resolution with 3.45 µm pixels.
*   **Global Shutter**: Eliminates motion blur and rolling shutter distortion in high-speed applications.
*   **Hardware Trigger & Strobe**: Dedicated pins for external trigger input and strobe output (no soldering required).
*   **Broad Compatibility**: Supports Raspberry Pi 3, 4, and 5 (Debian Bookworm/Trixie) and NVIDIA Jetson Orin Nano.
*   **Mono & Color Versions**: Compatible with both monochrome and color sensor variants.
*   **Native Driver Support**: Works directly with official kernel drivers for both platforms.

---

## Quick Start Guide — Raspberry Pi

### 1. Hardware Connection

Connect the camera to the CSI port of your Raspberry Pi using the appropriate ribbon cable. Ensure the connection is secure.

### 2. Enable the Driver

Modify the Raspberry Pi configuration file to enable the IMX296 overlay.

*   **For older OS versions**:
    ```bash
    sudo nano /boot/config.txt
    ```
*   **For the latest OS (Bookworm/Trixie)**:
    ```bash
    sudo nano /boot/firmware/config.txt
    ```

Add one of the following lines to the end of the file:

**For CAM0 port**:
```ini
dtoverlay=imx296,cam0
```

**For CAM1 port**:
```ini
dtoverlay=imx296,cam1
```

### 3. Reboot & Test

Reboot your Raspberry Pi:
```bash
sudo reboot
```

Test the camera using the `libcamera` suite:
```bash
# Preview the camera stream
libcamera-hello -t 0

# Capture a still image
libcamera-still -o test.jpg

# List available cameras
libcamera-hello --list-cameras
```

---

## Quick Start Guide — NVIDIA Jetson Orin Nano

### 1. Hardware Connection

Connect the camera to one of the CSI connectors on the Jetson Orin Nano carrier board using the appropriate ribbon cable.

### 2. Install Binary Driver Package

Extract and install the pre-compiled driver package:

```bash
cd 1-1jetson_orin_nano_driver
tar -xzf imx296_binary_package_20260427_blk0x070_v4.tar.gz
cd scripts
chmod +x install_binary.sh
sudo ./install_binary.sh
```

The installer will:
- Copy the kernel module (`imx296.ko`) to `/lib/modules/$(uname -r)/kernel/drivers/media/i2c/`
- Copy device tree overlays (`.dtbo` files) to `/boot/`
- Run `depmod -a` to update module dependencies

### 3. Configure CSI Overlay

Use NVIDIA's Jetson-IO tool to select the appropriate camera configuration:

```bash
sudo /opt/nvidia/jetson-io/jetson-io.py
```

In the menu, select:

1. **Configure Jetson 24pin CSI Connector**
2. **Configure for compatible hardware**
3. Pick the overlay matching your camera setup:
   - `Camera IMX296 Dual` — two IMX296 color sensors
   - `Camera IMX219 + IMX296` — IMX219 on CSI0, IMX296 on CSI1
   - `Camera IMX477 + IMX296` — IMX477 on CSI0, IMX296 on CSI1
   - `Camera IMX296MONO Dual` — two IMX296 mono sensors
   - `Camera IMX296MONO Single CSI0` — single IMX296 mono on CSI0
4. **Save pin changes** → **Save and reboot to reconfigure pins**

### 4. Verify Installation

Verify the driver is loaded:
```bash
lsmod | grep imx296
dmesg | grep imx296
```

### 5. Test Camera Preview

**For Monochrome Camera**:
```bash
./camera_control.sh
```

**For Color Camera**:
```bash
./camera_control_color.sh
```

**Manual GStreamer Preview** (with recommended indoor lighting settings):
```bash
gst-launch-1.0 nvarguscamerasrc num-buffers=30 \
    gainrange="4 4" exposuretimerange="200000 200000" \
    ! 'video/x-raw(memory:NVMM),width=1456,height=1088' \
    ! nvvidconv ! xvimagesink
```

### Camera Control Parameters

Supported control ranges for Jetson Orin Nano:

| Control | Min | Max | Unit | Notes |
|---|---|---|---|---|
| `gainrange` | 1 | 16 | linear multiplier | ≈ 0 … 24 dB |
| `exposuretimerange` | 1000 | 1000000 | nanoseconds | 1 µs … 1 ms |
| `framerate` | ~0.06 | ~60.4 | fps | Varies by resolution |

### Brightness Presets

Use the `adjust_brightness.sh` script for quick brightness adjustments:

| Preset | Gain | Exposure (ns) | Scene |
|---|---|---|---|
| 1 | 1 | 10,000 | Very dark / Reference |
| 2 | 1 | 50,000 | Bright outdoor |
| 3 | 2 | 100,000 | Normal |
| 4 | 4 | 200,000 | **Indoor (recommended start)** |
| 5 | 8 | 500,000 | Low light |

---

## Advanced Features: Hardware Trigger

The module supports hardware triggering via GPIO for both Raspberry Pi and Jetson platforms.

### Raspberry Pi Trigger Scripts

*   **Standard Trigger (`imx296.sh`)**: A loop script that toggles GPIO 23 to trigger the camera.
*   **Trixie/Bookworm Trigger (`imx296-trixie.sh`)**: Optimized trigger command for the latest OS versions using `gpioset`.

### Trigger Pinout

Refer to [`1-4Images/Conection.png`](./1-4Images/Conection.png) for the physical pin definitions of the trigger and strobe headers.

---

## I2C Tools & Diagnostics

### Pre-compiled I2C Tools

Pre-compiled I2C diagnostic tools are provided for both 32-bit and 64-bit systems:

*   **`i2c-tools-arch32/`**: 32-bit binaries (`i2c_read`, `i2c_write`)
*   **`i2c-tools-arch64/`**: 64-bit binaries (`i2c_read`, `i2c_write`)
*   **`i2c-tools-python-eeprom&strobe/`**: Python-based utilities for EEPROM and strobe control

### Python I2C Tools

For advanced I2C operations (EEPROM read/write, strobe control):

```bash
cd i2c-tools-python-eeprom\&strobe
python3 i2c.py --help
```

---

## Repository Structure

*   **`CAM-IMX296RAW-UserManual-V202.pdf`**: Latest technical manual with complete specifications.
*   **`1-1jetson_orin_nano_driver/`**: Pre-compiled binary driver package for NVIDIA Jetson Orin Nano.
*   **`imx296.sh` / `imx296-trixie.sh`**: Shell scripts for Raspberry Pi hardware trigger control.
*   **`1-4Images/`**: Connection diagrams and hardware reference images.
*   **`Old_Manual/`**: Legacy drivers and sample code (C/Python) for older Raspberry Pi kernel versions (5.4, 5.10, 6.1).
*   **`i2c-tools-arch32/` / `i2c-tools-arch64/`**: Pre-compiled I2C diagnostic tools.
*   **`i2c-tools-python-eeprom&strobe/`**: Python-based I2C utilities for EEPROM and strobe control.
*   **`Certifications/`**: CE and FCC compliance documents.

---

## Supported Platforms

| Platform | OS | Status | Notes |
|---|---|---|---|
| Raspberry Pi 3 | Bullseye, Bookworm | ✓ Supported | Legacy kernel support available |
| Raspberry Pi 4 | Bullseye, Bookworm, Trixie | ✓ Supported | Recommended for production |
| Raspberry Pi 5 | Bookworm, Trixie | ✓ Supported | Latest platform, fully optimized |
| NVIDIA Jetson Orin Nano | JetPack 6.0+ | ✓ Supported | Binary driver package included |

---

## Documentation & Support

*   **Official Documentation**: 
    - [Raspberry Pi Camera Guide](https://www.raspberrypi.com/documentation/computers/camera_software.html)
    - [NVIDIA Jetson Documentation](https://docs.nvidia.com/jetson/)
*   **User Manual**: See `CAM-IMX296RAW-UserManual-V202.pdf`
*   **Website**: [www.inno-maker.com](https://www.inno-maker.com)
*   **Email**: [support@inno-maker.com](mailto:support@inno-maker.com) | [sales@inno-maker.com](mailto:sales@inno-maker.com)

---

## Troubleshooting

### Camera Not Detected on Raspberry Pi

1. Verify the ribbon cable is properly seated in the CSI connector
2. Check that the overlay is correctly configured in `config.txt`
3. Verify the driver is loaded: `lsmod | grep imx296`
4. Check kernel messages: `dmesg | tail -20`

### Camera Not Detected on Jetson Orin Nano

1. Verify the ribbon cable is properly connected to the CSI port
2. Confirm the binary driver package is installed: `lsmod | grep imx296`
3. Verify the correct device tree overlay is loaded via Jetson-IO
4. Check system logs: `sudo dmesg | grep imx296`

### Low Image Quality or Brightness Issues

- Use the brightness preset scripts to adjust gain and exposure
- Refer to the control parameter ranges table above
- Consult the user manual for detailed image quality tuning

---

## License & Terms

This repository contains pre-built binaries, drivers, and utilities for the CAM-IMX296RAW-TRIGGER camera module. Use of these materials is subject to the terms and conditions provided by INNO-MAKER.

For detailed licensing information and terms of use, please contact our support team.
