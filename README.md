# KVM over USB
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![black_checks](https://badgen.net/github/checks/wevsty/KVM-over-USB/main?label=black)](https://github.com/wevsty/KVM-over-USB/actions/workflows/code_checks.yml)
[![flake8_checks](https://badgen.net/github/checks/wevsty/KVM-over-USB/main?label=flake8)](https://github.com/wevsty/KVM-over-USB/actions/workflows/code_checks.yml)
[![release_version](https://badgen.net/github/release/wevsty/KVM-over-USB)](https://github.com/wevsty/KVM-over-USB/releases)

一个简单的KVM USB方案

Documentation English Version: https://github.com/wevsty/KVM-over-USB/blob/main/README_en-us.md

## 简介
当服务器因为各种因素失去网络连接时想恢复工作是很困难的事，尽管有IPMI一类的技术可以帮助我们解决问题，但往往这类设备是昂贵的。 
对于家庭用户来说，本方案能帮助你使用其他PC/笔记本电脑通过USB连接快速的管理/维护服务器。 


## 硬件部分
因为对于普通用户来说，要求用户自行生产或者委托制造商生产硬件是不现实的，所以本项目推荐使用市面上已有的产品进行组合自行DIY。

### 硬件清单
1. 视频采集卡：可以使用MS2109或MS2130等芯片的视频采集卡，市场售价约为30到100元人民币。 
2. CH340转CH9329的USB连接线：
CH340是一个常见的USB转串口芯片，通过串口接入CH9329，最终将CH9329连接到被控制的设备即可。 
3. HDMI连接线。 
4. 如设备没有足够多的USB接口，建议搭配一个USB HUB使用。 

备注1：在购物平台上有成品的线，可直接购买，市场售价约20元人民币。 

备注2：如有特殊需要，也可以自行购入使用其他芯片的USB转串口连接线（比如：FT232）然后购买带有串行接口的CH9329模块使用。 

### 连接原理图
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/connection_schematic.svg)

### 硬件实物图
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/hardware_photos.jpg)

### 其他兼容硬件
根据网友反馈，由 Sipeed 生产的 NanoKVM-USB 亦可使用本项目提供的客户端。

## 软件
项目软件客户端基于 [KVM-Card-Mini-PySide6](https://github.com/ElluIFX/KVM-Card-Mini-PySide6) 的源码进行了改动以及重构，适配了 CH9329 作为键盘鼠标输入使用。


### 客户端编译

假定您已经安装好 git、python、poetry 后您可以执行如下命令进行编译。

```powershell
git clone https://github.com/wevsty/KVM-over-USB.git
cd client
poetry shell
poetry install
./compiler.ps1
```


### 客户端下载

请访问 releases 页面下载已编译好的客户端。

注意：目前客户端（控制端）仅提供 Windows 支持。

https://github.com/wevsty/KVM-over-USB/releases


### 使用方法

1. 如果您使用的USB转串口芯片为 CH340 ，您可能需要首先安装 CH340 的驱动程序。

CH340 驱动程序下载地址： https://www.wch.cn/downloads/CH341SER_EXE.html 

安装成功后可通过设备管理器查看串口端口号。

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/device_manager_port.png)

备注：端口号可能为随机非固定。

2. 执行 usb_kvm_client

视频连接： 
选择设备菜单 -> 视频设备 -> 选择正确的视频采集卡 -> 确定。 

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/video_device_setup.png)

控制器连接： 

大部分情况下，默认配置会自动选择串口。但若您的设备上拥有多个串口，您可能需要手动选择串口名称。 

选择设备菜单 -> 控制器设置 -> 选择正确的串口 -> 确定。 

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/controller_device_setup.png)

### 演示

演示控制ASUS BIOS 

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/demo_control_bios.gif)

演示自动输入功能 

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/demo_fast_input.gif)

### FAQ

Q: 为什么被控制端为 Linux 发行版时鼠标不工作？ 

A: 部分操作系统不支持鼠标使用绝对坐标模式，请尝试切换至相对坐标模式进行操作。 

Q: 如何发送 Ctrl + Alt + Delete 组合键？ 

A: 如需向被控制端发送这些组合键，建议使用键盘菜单中的快捷键功能。

Q: 使用软件时出现输入异常情况怎么办？ 

A: 请使用软件设备菜单中的重载或者重置功能，如使用后依然存在故障建议尝试重启被控制端的操作系统。 

Q: 快速粘贴或剪贴板输入时大小写不正确如何处理？ 

A: 请通过菜单中的同步指示器功能同步键盘状态后再尝试。


## 感谢

[Jackadminx](https://github.com/Jackadminx)/[KVM-Card-Mini](https://github.com/Jackadminx/KVM-Card-Mini)

[ElluIFX](https://github.com/ElluIFX)/[KVM-Card-Mini-PySide6](https://github.com/ElluIFX/KVM-Card-Mini-PySide6)

[binnehot](https://github.com/binnehot)/[KVM-over-USB](https://github.com/binnehot/KVM-over-USB)
