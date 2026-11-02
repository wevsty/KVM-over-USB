/*
 * USB 描述符定义：HID 键盘（Interface 0）+ HID 鼠标（Interface 1）+ CDC ACM（2/3）。
 * 结构取自 ESP-IDF v6.1 示例 examples/peripherals/usb/device/tusb_hid。
 *
 * SPDX-License-Identifier: MIT
 */

#include "usb_descriptors.h"

#include "tusb.h"
#include "class/hid/hid_device.h"

/* 本工程必须有且只有 2 个 HID 实例，否则接口数量与回调分支全部失配 */
#if (CFG_TUD_HID != 2)
#error "CONFIG_TINYUSB_HID_COUNT must be 2"
#endif

/* 本工程必须有且只有 1 个 CDC 实例（Interface 2/3） */
#if (CFG_TUD_CDC != 1)
#error "CONFIG_TINYUSB_CDC_COUNT must be 1"
#endif

/* 配置描述符总长度
 * = 配置描述符(9) + 2 x HID(9+9+7 = 25) + CDC(IAD 8 + comm 9 + header 5 +
 *   call mgmt 5 + ACM 4 + union 5 + notif EP 7 + data itf 9 + OUT EP 7 + IN EP 7 = 66)
 * = 9 + 25 + 25 + 66 = 125 = 0x7D */
#define TUSB_DESC_TOTAL_LEN     (TUD_CONFIG_DESC_LEN + 2 * TUD_HID_DESC_LEN + TUD_CDC_DESC_LEN)

/* 配置编号、接口数量、供电参数 */
#define USB_CONFIG_NUM          (1)
#define USB_CONFIG_ITF_COUNT    (4)
#define USB_CONFIG_POWER_MA     (100)

/* 报告在总线上的长度不得超过端点包长 */
_Static_assert(HID_KEYBOARD_REPORT_LEN <= HID_EP_SIZE_KEYBOARD,
               "keyboard report exceeds EP size");
_Static_assert(HID_MOUSE_REPORT_LEN_RELATIVE <= HID_EP_SIZE_MOUSE,
               "mouse relative report exceeds EP size");
_Static_assert(HID_MOUSE_REPORT_LEN_ABSOLUTE <= HID_EP_SIZE_MOUSE,
               "mouse absolute report exceeds EP size");

/**
 * @brief 键盘 HID 报告描述符
 *
 * 不传 HID_REPORT_ID()：Report ID 为 0，报告长度为 8 字节，
 * 这是 Boot Protocol 键盘的要求。
 */
const uint8_t hid_report_descriptor[] = {
    TUD_HID_REPORT_DESC_KEYBOARD()
};

/**
 * @brief 鼠标 HID 报告描述符
 *
 * Report ID 1 = 相对坐标，报告体 4 字节：buttons + dx + dy + wheel
 * Report ID 2 = 绝对坐标，报告体 6 字节：buttons + x(16) + y(16) + wheel
 */
const uint8_t hid_report_descriptor_mouse[] = {
    /* ===== Report ID 1：相对坐标（BIOS 可达路径）===== */
    HID_USAGE_PAGE(HID_USAGE_PAGE_DESKTOP),
    HID_USAGE(HID_USAGE_DESKTOP_MOUSE),
    HID_COLLECTION(HID_COLLECTION_APPLICATION),
      HID_REPORT_ID(HID_MOUSE_REPORT_ID_RELATIVE)           /* = 1，宏自带尾逗号 */
      HID_USAGE(HID_USAGE_DESKTOP_POINTER),
      HID_COLLECTION(HID_COLLECTION_PHYSICAL),
        HID_USAGE_PAGE(HID_USAGE_PAGE_BUTTON),
          HID_USAGE_MIN(1), HID_USAGE_MAX(5),
          HID_LOGICAL_MIN(0), HID_LOGICAL_MAX(1),
          HID_REPORT_COUNT(5), HID_REPORT_SIZE(1),
          HID_INPUT(HID_DATA | HID_VARIABLE | HID_ABSOLUTE),
          HID_REPORT_COUNT(1), HID_REPORT_SIZE(3),
          HID_INPUT(HID_CONSTANT),
        HID_USAGE_PAGE(HID_USAGE_PAGE_DESKTOP),
          HID_USAGE(HID_USAGE_DESKTOP_X),
          HID_USAGE(HID_USAGE_DESKTOP_Y),
          HID_USAGE(HID_USAGE_DESKTOP_WHEEL),
          HID_LOGICAL_MIN(-127), HID_LOGICAL_MAX(127),
          HID_REPORT_COUNT(3), HID_REPORT_SIZE(8),
          HID_INPUT(HID_DATA | HID_VARIABLE | HID_RELATIVE),
      HID_COLLECTION_END,
    HID_COLLECTION_END,
    /* ===== Report ID 2：绝对坐标 + wheel ===== */
    HID_USAGE_PAGE(HID_USAGE_PAGE_DESKTOP),
    HID_USAGE(HID_USAGE_DESKTOP_MOUSE),
    HID_COLLECTION(HID_COLLECTION_APPLICATION),
      HID_REPORT_ID(HID_MOUSE_REPORT_ID_ABSOLUTE)           /* = 2，宏自带尾逗号 */
      HID_USAGE(HID_USAGE_DESKTOP_POINTER),
      HID_COLLECTION(HID_COLLECTION_PHYSICAL),
        HID_USAGE_PAGE(HID_USAGE_PAGE_BUTTON),
          HID_USAGE_MIN(1), HID_USAGE_MAX(5),
          HID_LOGICAL_MIN(0), HID_LOGICAL_MAX(1),
          HID_REPORT_COUNT(5), HID_REPORT_SIZE(1),
          HID_INPUT(HID_DATA | HID_VARIABLE | HID_ABSOLUTE),
          HID_REPORT_COUNT(1), HID_REPORT_SIZE(3),
          HID_INPUT(HID_CONSTANT),
        HID_USAGE_PAGE(HID_USAGE_PAGE_DESKTOP),
          HID_USAGE(HID_USAGE_DESKTOP_X),
          HID_USAGE(HID_USAGE_DESKTOP_Y),
          HID_LOGICAL_MIN(0), HID_LOGICAL_MAX_N(32767, 2),
          HID_REPORT_COUNT(2), HID_REPORT_SIZE(16),
          HID_INPUT(HID_DATA | HID_VARIABLE | HID_ABSOLUTE),
          /* 绝对坐标集合内的 wheel（相对量，对应协议 §10 第 6 字节） */
          HID_USAGE(HID_USAGE_DESKTOP_WHEEL),
          HID_LOGICAL_MIN(-127), HID_LOGICAL_MAX(127),
          HID_REPORT_COUNT(1), HID_REPORT_SIZE(8),
          HID_INPUT(HID_DATA | HID_VARIABLE | HID_RELATIVE),
      HID_COLLECTION_END,
    HID_COLLECTION_END,
};

/**
 * @brief 字符串描述符
 */
const char *hid_string_descriptor[USB_STRING_DESC_COUNT] = {
    (char[]){0x09, 0x04},   /* 0: 语言 ID，English (0x0409) */
    "Espressif",            /* 1: Manufacturer */
    "KVM Controller",       /* 2: Product */
    "123456",               /* 3: Serial */
    "KVM HID Keyboard",     /* 4: 键盘接口字符串 */
    "KVM HID Mouse",        /* 5: 鼠标接口字符串 */
    "KVM CDC",              /* 6: CDC 接口字符串 */
};

/**
 * @brief 配置描述符：1 个配置，4 个接口
 *
 * Interface 0 = 键盘（bInterfaceSubClass=1, bInterfaceProtocol=1，Boot）
 * Interface 1 = 鼠标（bInterfaceSubClass=0, bInterfaceProtocol=0，Report）
 * Interface 2 = CDC Comm（Class 0x02 / SubClass 0x02 / Protocol 0x00）
 * Interface 3 = CDC Data（Class 0x0A），随 Interface 2 的 IAD 一起声明
 */
const uint8_t hid_configuration_descriptor[] = {
    /* 配置号, 接口数, 字符串索引, 总长度, 属性, 电流(mA) */
    TUD_CONFIG_DESCRIPTOR(USB_CONFIG_NUM, USB_CONFIG_ITF_COUNT, USB_STR_IDX_LANGID,
                          TUSB_DESC_TOTAL_LEN, TUSB_DESC_CONFIG_ATT_REMOTE_WAKEUP,
                          USB_CONFIG_POWER_MA),

    /* 接口号, 字符串索引, boot protocol, 报告描述符长度, EP IN 地址, EP 大小, 轮询间隔 */
    TUD_HID_DESCRIPTOR(USB_HID_ITF_KEYBOARD, USB_STR_IDX_HID_KEYBOARD, HID_ITF_PROTOCOL_KEYBOARD,
                       sizeof(hid_report_descriptor), USB_HID_EP_IN_KEYBOARD,
                       HID_EP_SIZE_KEYBOARD, HID_EP_POLL_MS_KEYBOARD),

    TUD_HID_DESCRIPTOR(USB_HID_ITF_MOUSE, USB_STR_IDX_HID_MOUSE, HID_ITF_PROTOCOL_NONE,
                       sizeof(hid_report_descriptor_mouse), USB_HID_EP_IN_MOUSE,
                       HID_EP_SIZE_MOUSE, HID_EP_POLL_MS_MOUSE),

    /* CDC ACM：Interface 2（Comm）+ Interface 3（Data），宏内自带 IAD，共 66 字节
     * notif EP 0x83（IN, interrupt, 8B, bInterval=1）
     * data  EP 0x01（OUT, bulk, 64B）/ 0x84（IN, bulk, 64B） */
    TUD_CDC_DESCRIPTOR(USB_CDC_ITF_COMM, USB_STR_IDX_CDC,
                       USB_CDC_EP_NOTIF, USB_CDC_EP_NOTIF_SIZE,
                       USB_CDC_EP_DATA_OUT, USB_CDC_EP_DATA_IN,
                       USB_CDC_EP_DATA_SIZE),
};

/* 数组实际长度必须与 wTotalLength 声明一致，否则主机会因描述符截断而枚举失败 */
_Static_assert(sizeof(hid_configuration_descriptor) == TUSB_DESC_TOTAL_LEN,
               "configuration descriptor length mismatch");
_Static_assert(TUSB_DESC_TOTAL_LEN <= 0xFF, "wTotalLength must fit in uint8_t");