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
- [https://www.raspberrypi.com/documentation/computers/camera_softwarehtml](https://www.raspberrypi.com/documentation/computers/camera_softwarehtml)


## Exteral Trigger Function
![External Trigger Function](https://github.com/INNO-MAKER/cam-imx296raw-trigger/blob/main/1-4Images/Signal.jpg "IMX296 External Tigger")

- How to Enable External Trigger 
  - Step1, sudo su
  - Step2, echo 1 > /sys/module/imx296/parameters/trigger_mode

## Strobe Wire 
- The Global Shutter (GS) camera can be triggered externally by pulsing the external trigger (denoted on the board as XTR（Trig+）,GND(Trig-)) connection on the board. Multiple cameras can be connected to the same pulse, allowing for an alternative way to synchronise two cameras.

- The exposure time is equal to the low pulse-width time plus an additional 14.26us. i.e. a low pulse of 10000us leads to an exposure time of 10014.26us. Framerate is directly controlled by how often you pulse the pin. A PWM frequency of 30Hz will lead to a framerate of 30 frames per second.

![IMX296 Camera Module](https://www.inno-maker.com/wp-content/uploads/2021/05/Raspberry_Pi_Global_Shutter_Camera_IMX296LLR-C_CMOS_Sensor_External_Trigger_up_to_60fps_1456x1088_Pixels_Fish-Eye_Lens_FOV160_Module_for_Pi_4B_Pi_3B_Pi_3B_Pi_3A_CM4_CM3_CM3_04.jpg "IMX296")

![IMX296](https://github.com/INNO-MAKER/cam-imx296raw-trigger/blob/main/1-4Images/Conection.png "IMX296")

## Strobe Manual 

- IMX296 official driver that provide by RPI default kernel not enable strobe by default.

- Imx296  can output strobe while work in normal or fast trigger mode.
We can enable strobe by i2c tools.

I2c tools write register:
./i2c_write  4  0x1a <reg addr> <reg val>

I2c tools read register:
./i2c_read  4  0x1a <reg addr> <num of regs regs to read>



## More Information
- https://github.com/raspberrypi/documentation/tree/develop/documentation/asciidoc/accessories/camera