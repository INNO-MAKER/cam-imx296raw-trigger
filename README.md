![IMX296 Camera Module](https://www.inno-maker.com/wp-content/uploads/2021/06/IMX296-MIPI-4.jpg "IMX296")



# Feature
- Support Raspberry Pi OS Driver directly
- Support external Trigger And stobe, we reserve pins no need to solder;
- Support mono version and color version imx296

## Quick Start 
#### Step1, Modify config.txt
- sudo nano /boot/config.txt
  - For the latest version raspberry Pi OS, it should be
- sudo nano /boot/firmware/config.txt

#### Step2, Add below content to the last line
- dtoverlay=imx296

#### Step3, Reboot and use below command to preview
- libcamera-hello -t 0

#### More information
- [https://www.raspberrypi.com/documentation/computers/camera_software.html](https://www.raspberrypi.com/documentation/computers/camera_software.html)


## User Manual 
- [CAM-IMX296RAW-UserManual-V2.0.pdf](https://github.com/INNO-MAKER/cam-imx296raw-trigger/blob/main/CAM-IMX296RAW-UserManual-V2.0.pdf )