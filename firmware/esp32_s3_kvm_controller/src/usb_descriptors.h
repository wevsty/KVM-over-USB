/*
 * USB 描述符接口：接口号 / 端点号 / 报告长度等常量。
 * 键盘必须是 Interface 0（BIOS 兼容），CDC ACM 放最后。
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 字符串描述符索引，必须与 hid_string_descriptor[] 的顺序一致 */
#define USB_STR_IDX_LANGID        0
#define USB_STR_IDX_MANUFACTURER  1
#define USB_STR_IDX_PRODUCT       2
#define USB_STR_IDX_SERIAL        3
#define USB_STR_IDX_HID_KEYBOARD  4
#define USB_STR_IDX_HID_MOUSE     5
#define USB_STR_IDX_CDC           6

/* hid_string_descriptor[] 的条目数
 * esp_tinyusb 上限 USB_STRING_DESCRIPTOR_ARRAY_SIZE = 8，
 * 超过会返回 ESP_ERR_NOT_SUPPORTED。 */
#define USB_STRING_DESC_COUNT     7

/* 接口号：键盘必须是 Interface 0（BIOS 兼容），鼠标跟在后面 */
#define USB_HID_ITF_KEYBOARD      0
#define USB_HID_ITF_MOUSE         1

/* TinyUSB 的 HID 实例编号 = 配置描述符中 HID 接口出现的顺序 */
#define HID_INSTANCE_KEYBOARD     0
#define HID_INSTANCE_MOUSE        1

/* 端点地址：键盘 0x81、鼠标 0x82 */
#define USB_HID_EP_IN_KEYBOARD    0x81
#define USB_HID_EP_IN_MOUSE       0x82

/* 端点包长（字节），必须 >= 对应报告在总线上的最大长度 */
#define HID_EP_SIZE_KEYBOARD      8
#define HID_EP_SIZE_MOUSE         8

/* 端点轮询间隔（ms） */
#define HID_EP_POLL_MS_KEYBOARD   10
#define HID_EP_POLL_MS_MOUSE      8

/* ===== CDC ACM：Interface 2 = Comm，Interface 3 = Data ===== */
#define USB_CDC_ITF_COMM          2
#define USB_CDC_ITF_DATA          3

/* 端点地址：非 EP0 的 IN 端点只有 4 个（0x81/0x82 已给 HID），
 * 剩下 0x83 给 notif、0x84 给 data IN；data OUT 用 0x01。 */
#define USB_CDC_EP_NOTIF          0x83
#define USB_CDC_EP_DATA_OUT       0x01
#define USB_CDC_EP_DATA_IN        0x84

/* 中断通知端点包长固定 8；Bulk 数据端点包长全速最大 64 */
#define USB_CDC_EP_NOTIF_SIZE     8
#define USB_CDC_EP_DATA_SIZE      64

/* Boot Protocol 键盘报告固定 8 字节：modifier + reserved + 6 x keycode */
#define HID_KEYBOARD_REPORT_LEN   8

/* 鼠标 Report ID：1 = 相对坐标，2 = 绝对坐标 */
#define HID_MOUSE_REPORT_ID_RELATIVE   1
#define HID_MOUSE_REPORT_ID_ABSOLUTE   2

/* 鼠标报告在总线上的长度（含 Report ID 那 1 字节） */
#define HID_MOUSE_REPORT_LEN_RELATIVE  5   /* ID + buttons + dx + dy + wheel */
/* ID + buttons + x(16bit) + y(16bit) + wheel */
#define HID_MOUSE_REPORT_LEN_ABSOLUTE  7

/* 描述符本体，定义在 usb_descriptors.c */
extern const uint8_t hid_report_descriptor[];        /* 键盘报告描述符 */
extern const uint8_t hid_report_descriptor_mouse[];  /* 鼠标报告描述符 */
extern const char *hid_string_descriptor[USB_STRING_DESC_COUNT];
extern const uint8_t hid_configuration_descriptor[];

#ifdef __cplusplus
}
#endif