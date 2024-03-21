# Feature
- Support Raspberry Pi OS Driver directly
- Support external Trigger And stobe, we reserve pins no need to solder;
- Support mono version and color version imx296

## Quick Start
- Add below content to /boot/config.txt.
You may need to alter the camera configuration in your /boot/firmware/config.txt file.
  - dtoverlay=imx296
- More information please see [https://www.raspberrypi.com/documentation/computers/camera_softwarehtml](https://www.raspberrypi.com/documentation/computers/camera_softwarehtml)