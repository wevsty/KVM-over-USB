# KVM over USB
[![Python version](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![black_check](https://badgen.net/github/checks/wevsty/KVM-over-USB/main?label=black_check)](https://github.com/wevsty/KVM-over-USB/actions/workflows/code_checks.yml)
[![flake8_check](https://badgen.net/github/checks/wevsty/KVM-over-USB/main?label=flake8_check)](https://github.com/wevsty/KVM-over-USB/actions/workflows/code_checks.yml)
[![release_version](https://badgen.net/github/release/wevsty/KVM-over-USB)](https://github.com/wevsty/KVM-over-USB/releases)

一个简单的KVM USB方案

Documentation English Version: https://github.com/wevsty/KVM-over-USB/blob/main/README_en-us.md

## 简介
当服务器因为各种因素失去网络连接时想恢复工作是很困难的事，尽管有IPMI一类的技术可以帮助我们解决问题，但往往这类设备是昂贵的。 
对于家庭用户来说，本方案能帮助你使用其他PC/笔记本电脑通过USB连接快速的管理/维护服务器。 


## 硬件部分
因为对于普通用户来说，要求用户自行生产或者委托制造商生产硬件是不现实的，所以本项目推荐使用市面上已有的产品进行组合。

### 硬件清单
1. 视频采集卡：可以使用 MS2109 或 MS2130 等芯片的视频采集卡，市场售价约为30至100元人民币。 
2. CH340转CH9329的USB连接线。
3. HDMI连接线。 
4. 如设备没有足够多的USB接口，建议搭配一个USB HUB使用。 

特殊说明：
CH340是一个常见的USB转串口芯片，通过串口接入CH9329 。如有需要亦可使用其他USB转串口芯片。 

推荐CH340转CH9329的连接线是因为在购物平台上有成品的线，可直接购买，比较容易取得。目前市场售价约20元人民币。 
 
如有特殊需要，也可以自行购入使用其他芯片的USB转串口连接线（比如：FT232）然后购买带有串行接口的CH9329模块使用。 

### 连接原理图
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/connection_schematic.svg)

### 硬件实物图
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/hardware_photos.jpg)

### 其他兼容硬件
此外本项目客户端亦可兼容部分同类型产品，具体信息参考下表。

| 制造商 | 产品名 | 设备类型 |
| --- | --- | --- |
| - | KVM-Card-Mini | KVM-Card-Mini 系列 |
| Sipeed | NanoKVM-USB | CH9329 系列 |

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

https://github.com/wevsty/KVM-over-USB/releases


### Windows下使用方法

#### 1. 将硬件连接至计算机。
注意：如果您使用的USB转串口芯片为 CH340 ，您可能需要首先安装 CH340 的驱动程序。

CH340 驱动程序下载地址： https://www.wch.cn/downloads/CH341SER_EXE.html 

安装成功后可通过设备管理器查看串口端口号。 

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/device_manager_port.png)

#### 2. 执行客户端

选择设备菜单 -> 设置 -> 选择视频摄像头以及控制器 -> 确定。 

![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/settings.png)

设定完毕后可以使用 设备菜单 -> 连接 进行连接。 

### 其他操作系统用户

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
