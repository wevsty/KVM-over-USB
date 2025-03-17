# KVM over USB
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![usb_kvm_client_release](https://github.com/wevsty/KVM-over-USB/actions/workflows/usb_kvm_client_release.yml/badge.svg)](https://github.com/wevsty/KVM-over-USB/actions/workflows/usb_kvm_client_release.yml)

A simple KVM USB solution


## Synopsis
When a server loses network connectivity, it can be difficult to get back to work. Although there are technologies like IPMI that can help us to solve the problem, often such devices are expensive.
For home users, this project helps you to quickly manage/maintain your server using other PCs/laptops connected via USB.


## Hardware
Because for normal users, it is unrealistic to ask users to produce their own or commissioned manufacturers to produce hardware. so this project recommends the use of existing products on the market for a combination of DIY.


### Hardware list
1. Video capture card: You can use video capture cards with chips such as MS2109 or MS2130, which are sold in the market for about 5-15 USD. 
2. CH340 to CH9329 USB Connection Cable: CH340 is a common USB to serial chip, access CH9329 through the serial port, and finally connect CH9329 to the controlled device can be. 
3. HDMI cable. 
4. If the device does not have enough USB ports, it is recommended to use it with a USB HUB. 

Note 1: There are finished cables available on shopping platforms, which can be purchased directly at a market price of about 20 CNY. 
Note 2: If you have special needs, you can also purchase a USB to serial cable with other chips (e.g. FT232) and then purchase a CH9329 module with a serial interface. 

### Schematic
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/connection_schematic.svg)

### Hardware photos
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/hardware_photos.jpg)

### Other Compatible Hardware 
According to the feedback from our users, the NanoKVM-USB manufactured by Sipeed can also be used with the client provided in this project.

## Software
The software client of the project is based on the source code of [KVM-Card-Mini-PySide6](https://github.com/ElluIFX/KVM-Card-Mini-PySide6) with modifications, and adapts CH9329 for keyboard and mouse input.


### Client build

Assuming you have git, python, and poetry installed, you can run the following commands to compile.
```powershell
git clone https://github.com/wevsty/KVM-over-USB.git
cd client
poetry shell
poetry install
./compiler.ps1
```


### Client download

Please visit the releases page to download the compiled client.
Note: Currently the client (console) is only supported for Windows.

https://github.com/wevsty/KVM-over-USB/releases


### Usage

1. If you are using the CH340 USB to serial chip, you may need to install the CH340 driver first.

CH340 driver download address: https://www.wch.cn/downloads/CH341SER_EXE.html
After successful installation, you can check the serial port number through the device manager.

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/device_manager_port.png)

Note: The port number may be randomized and not fixed.

2. Execute usb_kvm_client

Video Connection:

Select Device menu -> Video Device -> Select the correct video capture card -> OK.

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/video_device_setup.png)

Controller Connection:
In most cases, the default configuration will automatically select the serial port, but if you have more than one serial port on your device, you may need to manually select the serial port name.

Select Device Menu -> Controller Settings -> Select the correct serial port -> OK.

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/controller_device_setup.png)

### Demo

Demo control ASUS BIOS
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/demo_control_bios.gif)

Demo auto input function
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/demo_fast_input.gif)

### FAQ

Q: Why does the mouse not work when the controlled end is a Linux distribution?

A: Some operating systems do not support the absolute coordinate mode of the mouse. Please try to switch to the relative coordinate mode for operation.

Q: How to send the Ctrl + Alt + Delete key combination?

A: If you need to send these key combinations to the controlled end, it is recommended to use the shortcut key function in the keyboard menu.

Q: What should I do if input is abnormal when using the software?

A: Please use the reload or reset function in the software device menu. If the problem still exists after using it, it is recommended to try to restart the operating system of the controlled end.

Q: How to deal with incorrect capitalization when quick pasting or clipboard input?

A: Please synchronize the keyboard status through the synchronization indicator function in the menu and try again.


## Thanks

[Jackadminx](https://github.com/Jackadminx)/[KVM-Card-Mini](https://github.com/Jackadminx/KVM-Card-Mini)

[ElluIFX](https://github.com/ElluIFX)/[KVM-Card-Mini-PySide6](https://github.com/ElluIFX/KVM-Card-Mini-PySide6)

[binnehot](https://github.com/binnehot)/[KVM-over-USB](https://github.com/binnehot/KVM-over-USB)
