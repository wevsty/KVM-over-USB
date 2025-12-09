# KVM over USB
[![Python version](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![flake8_check](https://badgen.net/github/checks/wevsty/KVM-over-USB/main?label=flake8_check)](https://github.com/wevsty/KVM-over-USB/actions/workflows/code_checks.yml)
[![release_version](https://badgen.net/github/release/wevsty/KVM-over-USB)](https://github.com/wevsty/KVM-over-USB/releases)

A simple KVM USB solution

## Introduction

It can be difficult to restore a server's functionality when it loses its network connection for various reasons. Although technologies like IPMI can help solve the problem, such devices are often expensive.
For home users, this solution can help you quickly manage or maintain servers using another PC connected via USB.

## Hardware

The software for this project already supports products related to the CH9329 and KVM-Card-Mini series. Users can choose the appropriate hardware based on their preferences.

Note: This project will try its best to maintain a consistent experience between different hardware, but due to the limitations of the hardware itself, some functions may be limited.

### CH9329 Series

For details, please refer to the documentation: [CH9329 Series](https://github.com/wevsty/KVM-over-USB/blob/main/document/CH9329_series_en.md)

### KVM-Card-Mini Series

For details, please refer to the documentation: [KVM-Card-Mini Series](https://github.com/wevsty/KVM-over-USB/blob/main/document/KVM-Card-Mini_series_en.md)

## Software

The project's software client is based on a modified and refactored version of the source code from [KVM-Card-Mini-PySide6](https://github.com/ElluIFX/KVM-Card-Mini-PySide6), adapted to use the CH9329 for keyboard and mouse input.

### Client Compilation

Assuming you have git, python, and uv installed, you can compile by executing the following commands.

```powershell
git clone https://github.com/wevsty/KVM-over-USB.git
cd client
uv venv
uv sync
# Execute compiler.ps1 and modify it according to the actual environment
./compiler.ps1

```

### Client Download

Please visit the releases page to download the compiled client.

https://github.com/wevsty/KVM-over-USB/releases

### How to use on Windows

1. Connect the hardware to the computer.

Note: If you are using a CH340 USB to serial chip, you may need to install the CH340 driver first.

CH340 driver download address: https://www.wch.cn/downloads/CH341SER_EXE.html

After successful installation, you can view the serial port number through Device Manager.

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/device_manager_port.png)

If you are using KVM-Card-Mini series hardware, no driver installation is required after connecting to the computer; it is plug-and-play.

2. Run the client

Select Device menu -> Settings -> Select video camera and controller -> OK.

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/settings.png)

After setting up, you can connect using Device menu -> Connect.

### Linux Users

This client is now supported on Linux distributions such as Ubuntu.

It should be noted that when using it on Linux, you need to pay attention to permissions.

For example:
When the hardware is KVM-Card-Mini, you need to set HID access permissions or grant the program root privileges before use.

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

### MacOS Users

This project has preliminary support for MacOS, but has not undergone any testing and does not provide pre-compiled binaries. If you need to use it on MacOS, please compile and run from the source code yourself.

### Demonstration

Demo controlling ASUS BIOS

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/demo_control_bios.gif)

Demo automatic input function

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/demo_fast_input.gif)

### FAQ

Q: Why doesn't the mouse work when the controlled end is a Linux distribution?

A: Some operating systems do not support the mouse in absolute coordinate mode. Please try switching to relative coordinate mode for operation.

Q: How to send the Ctrl + Alt + Delete key combination?

A: To send these key combinations to the controlled end, it is recommended to use the shortcut function in the Keyboard menu.

Q: What should I do if there is an input abnormality when using the software?

A: Please use the reload or reset function in the software's device menu. If the problem persists after use, it is recommended to try restarting the controlled end's operating system.

Q: What should I do if the case is incorrect when fast-pasting or using clipboard input?

A: Please sync the keyboard status using the sync indicator function in the menu before trying again.

## Thanks

[Jackadminx](https://github.com/Jackadminx)/[KVM-Card-Mini](https://github.com/Jackadminx/KVM-Card-Mini)

[ElluIFX](https://github.com/ElluIFX)/[KVM-Card-Mini-PySide6](https://github.com/ElluIFX/KVM-Card-Mini-PySide6)

[binnehot](https://github.com/binnehot)/[KVM-over-USB](https://github.com/binnehot/KVM-over-USB)
