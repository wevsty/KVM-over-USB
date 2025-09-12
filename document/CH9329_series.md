# KVM Hardware CH9329 系列

## DIY硬件清单
1. 视频采集卡：可以使用MS2109或MS2130等芯片的视频采集卡，市场售价约为30至100元人民币。 
2. CH340转CH9329的USB连接线。
3. HDMI连接线。 
4. 如设备没有足够多的USB接口，建议搭配一个USB HUB使用。 

特殊说明：
CH340是一个常见的USB转串口芯片，通过串口接入CH9329 。如有需要亦可使用其他USB转串口芯片。 

推荐CH340转CH9329的连接线是因为在购物平台上有成品的线，可直接购买，比较容易取得。目前市场售价约20元人民币。 
 
如有特殊需要，也可以自行购入使用其他芯片的USB转串口连接线（比如：FT232）然后购买带有串行接口的CH9329模块自行连接使用。 

## 连接原理图
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/connection_schematic.svg)

## 硬件实物图
![image](https://github.com/wevsty/KVM-over-USB/blob/main/document/hardware_photos.jpg)

### 其他兼容硬件
此外本项目客户端亦可兼容部分同类型产品，具体信息参考下表。

| 制造商 | 产品名 | 设备类型 |
| --- | --- | --- |
| Sipeed | NanoKVM-USB | CH9329 系列 |
