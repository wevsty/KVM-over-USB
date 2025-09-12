# KVM over USB
[![Python version](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![flake8_check](https://badgen.net/github/checks/wevsty/KVM-over-USB/main?label=flake8_check)](https://github.com/wevsty/KVM-over-USB/actions/workflows/code_checks.yml)
[![release_version](https://badgen.net/github/release/wevsty/KVM-over-USB)](https://github.com/wevsty/KVM-over-USB/releases)

一个简单的KVM USB方案

Documentation English Version: https://github.com/wevsty/KVM-over-USB/blob/main/README_en.md

## 简介

当服务器因为各种因素失去网络连接时想恢复工作是很困难的事，尽管有IPMI一类的技术可以帮助我们解决问题，但往往这类设备是昂贵的。 
对于家庭用户来说，本方案能帮助你使用其他PC通过USB连接快速的管理或者维护服务器。 


## 硬件部分

本项目软件部分已支持 CH9329 和 KVM-Card-Mini 系列有关产品，用户可以根据自身喜好选择合适的硬件。

注：本项目将尽力保持不同硬件之间体验一致，但受限制于硬件本身，部分功能可能受限。

### CH9329 系列

详情参见文档：[CH9329系列](https://github.com/wevsty/KVM-over-USB/blob/main/document/CH9329_series.md)

### KVM-Card-Mini 系列

详情参见文档：[KVM-Card-Mini系列](https://github.com/wevsty/KVM-over-USB/blob/main/document/KVM-Card-Mini_series.md)


## 软件

项目软件客户端基于 [KVM-Card-Mini-PySide6](https://github.com/ElluIFX/KVM-Card-Mini-PySide6) 的源码进行了改动以及重构，适配了 CH9329 作为键盘鼠标输入使用。


### 编译客户端

假定您已经安装好 git、python、poetry 后您可以执行如下命令进行编译。

```powershell
git clone https://github.com/wevsty/KVM-over-USB.git
cd client
poetry env activate
poetry install
# 执行 compiler.ps1 请根据实际环境进行修改
./compiler.ps1
```


### 客户端下载

请访问 releases 页面下载已编译好的客户端。

https://github.com/wevsty/KVM-over-USB/releases


### Windows下使用方法

#### 1. 将硬件连接至计算机。
注意：如果您使用的USB转串口芯片为 CH340 ，您可能需要首先安装 CH340 的驱动程序。

CH340 驱动程序下载地址： https://www.wch.cn/downloads/CH341SER_EXE.html 

安装成功后可通过设备管理器查看串口端口号。 

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/device_manager_port.png)

如果您使用的是 KVM-Card-Mini 系列硬件，连接到电脑后无需安装任何驱动可即插即用。

#### 2. 执行客户端

选择设备菜单 -> 设置 -> 选择视频摄像头以及控制器 -> 确定。 

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/settings.png)

设定完毕后可以使用 设备菜单 -> 连接 进行连接。 

### Linux用户

本客户端目前已支持在 ubuntu 等 Linux 发行版上使用。

需要注意的是在 Linux 下使用时需要注意权限问题。

举例：
当硬件为 KVM-Card-Mini 时，使用之前需要设置 HID 访问权限或授予程序 root 权限。

以下代码将允许任何用户访问 KVM-Card-Mini 提供的 HID 设备。
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

### MacOS用户

本项目已初步支持MacOS，但未进行任何测试亦不提供编译好的二进制文件，如需要在MacOS上使用请使用源码自行进行编译运行。

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
