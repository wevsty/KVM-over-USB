# KVM over USB
[![Python version](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![black_check](https://badgen.net/github/checks/wevsty/KVM-over-USB/main?label=black_check)](https://github.com/wevsty/KVM-over-USB/actions/workflows/code_checks.yml)
[![flake8_check](https://badgen.net/github/checks/wevsty/KVM-over-USB/main?label=flake8_check)](https://github.com/wevsty/KVM-over-USB/actions/workflows/code_checks.yml)
[![release_version](https://badgen.net/github/release/wevsty/KVM-over-USB)](https://github.com/wevsty/KVM-over-USB/releases)

A simple KVM USB solution


## Synopsis
When a server loses network connectivity, it can be difficult to get back to work. Although there are technologies like IPMI that can help us to solve the problem, often such devices are expensive.
For home users, this project helps you to quickly manage/maintain your server using other PCs/laptops connected via USB.


## Hardware
Because for normal users, it is unrealistic to ask users to produce their own or commissioned manufacturers to produce hardware. so this project recommends the use of existing products on the market for a combination of DIY.


### Hardware list
1. Video capture card: Video capture cards using chips such as MS2109 or MS2130 can be used, with market prices ranging from approximately 5 - 20 USD.  
2. USB cable for converting CH340 to CH9329.  
3. HDMI cable.  
4. If the device does not have enough USB ports, it is recommended to use a USB hub. 

Special notes:  
CH340 is a common USB-to-serial port chip that connects to CH9329 via a serial port. Other USB-to-serial port chips can also be used if needed. 

The CH340 to CH9329 connection cable is recommended because finished cables are available for purchase on shopping platforms, making them easier to obtain. The current market price is approximately 2 - 5 USD.
 
If there are special requirements, you can also purchase USB-to-serial port connection cables using other chips (e.g., FT232) and then use a CH9329 module with a serial interface.

### Schematic
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/connection_schematic.svg)

### Hardware photos
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/hardware_photos.jpg)

### Other Compatible Hardware 
In addition, this project's client software is also compatible with some similar products. For specific information, please refer to the table below.

| Manufacturer | Product Name | Device Type |
| --- | --- | --- |
| - | KVM-Card-Mini | KVM-Card-Mini Series |
| Sipeed | NanoKVM-USB | CH9329 Series |

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

https://github.com/wevsty/KVM-over-USB/releases


### How to use on Windows

#### 1. Connect the hardware to the computer.  
Note: If you are using a CH340 USB-to-serial chip, you may need to install the CH340 driver first.

CH340 driver download link: https://www.wch.cn/downloads/CH341SER_EXE.html  

After successful installation, you can view the serial port number via Device Manager.  

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/device_manager_port.png)

#### 2. Run the client

Select Device Menu -> Settings -> Select Video Camera and Controller -> OK. 

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/settings.png)

After configuration, you can connect using Device Menu -> Connect.

### Other operating system users

This client currently supports use on Linux distributions such as Ubuntu.

Please note that when using Linux, you need to pay attention to permission issues.

Example:
When the hardware is KVM-Card-Mini, you need to set HID access permissions or grant root permissions to the program before use.

The following code will allow any user to access the HID device provided by KVM-Card-Mini.

```bash
sudo -s
cat > /etc/udev/rules.d/99-kvm-card-mini.rules << EOF
# KVM Card Mini
SUBSYSTEM=="usb", ATTRS{idVendor}=="413d", ATTRS{idProduct}=="2107", MODE="0666"
KERNEL=="hidraw*", ATTRS{idVendor}=="413d", ATTRS{idProduct}=="2107", MODE="0666"

EOF
udevadm control --reload-rules
udevadm trigger
```

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
