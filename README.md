# CAM-IMX296RAW-TRIGGER Camera Module

![IMX296 Camera Module](https://www.inno-maker.com/wp-content/uploads/2021/06/IMX296-MIPI-4.jpg "IMX296")

The **CAM-IMX296RAW-TRIGGER** is an industrial-grade camera module for Raspberry Pi, featuring the **Sony IMX296** global shutter CMOS sensor. It is designed for high-speed motion capture, automation, and machine vision applications where rolling shutter distortion must be eliminated.

This module is fully compatible with the official Raspberry Pi camera driver and supports advanced features like hardware trigger and strobe synchronization.

---

## Key Features

*   **Sony IMX296 Global Shutter Sensor**: 1.58 MP (1456 x 1088) resolution with 3.45 µm pixels.
*   **Global Shutter**: Eliminates motion blur and rolling shutter distortion in high-speed applications.
*   **Native Driver Support**: Works directly with the official Raspberry Pi `imx296` kernel driver.
*   **Hardware Trigger & Strobe**: Dedicated pins for external trigger input and strobe output (no soldering required).
*   **Broad Compatibility**: Supports Raspberry Pi 3, 4, and 5 (including the latest Debian Bookworm/Trixie OS).
*   **Mono & Color Versions**: Compatible with both monochrome and color sensor variants.

---

## Quick Start Guide

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

Add the following line to the end of the file:
```text
dtoverlay=imx296
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
```

---

## Advanced Features: Hardware Trigger

The module supports hardware triggering via GPIO. Example scripts are provided in the repository:

*   **Standard Trigger (`imx296.sh`)**: A loop script that toggles GPIO 23 to trigger the camera.
*   **Trixie/Bookworm Trigger (`imx296-trixie.sh`)**: Optimized trigger command for the latest OS versions using `gpioset`.

### Trigger Pinout
Refer to the [`1-4Images/Conection.png`](./1-4Images/Conection.png) for the physical pin definitions of the trigger and strobe headers.

---

## Repository Structure

*   [`CAM-IMX296RAW-UserManual-V202.pdf`](./CAM-IMX296RAW-UserManual-V202.pdf): Latest technical manual.
*   [`imx296.sh`](./imx296.sh) / [`imx296-trixie.sh`](./imx296-trixie.sh): Shell scripts for hardware trigger control.
*   [`Old_Manual/`](./Old_Manual/): Legacy drivers and sample code (C/Python) for older kernel versions (5.4, 5.10, 6.1).
*   [`i2c-tools-arch64/`](./i2c-tools-arch64/): Pre-compiled I2C diagnostic tools for 64-bit systems.
*   [`Certifications/`](./Certifications/): CE and FCC compliance documents.

---

## Documentation & Support

*   **Official Documentation**: [Raspberry Pi Camera Guide](https://www.raspberrypi.com/documentation/computers/camera_software.html)
*   **Website**: [www.inno-maker.com](https://www.inno-maker.com)
*   **Email**: [support@inno-maker.com](mailto:support@inno-maker.com) | [sales@inno-maker.com](mailto:sales@inno-maker.com)
