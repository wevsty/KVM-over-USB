/*
 * USB HID 实现：TinyUSB 回调 + 键盘 LED 状态缓存 + HID 报告发送。
 * 报告只在 CONTROL 下、由收到的帧触发发送（第 10 / 11 条）；SET_REPORT 只缓存不回发。
 *
 * SPDX-License-Identifier: MIT
 */

#include "hid.h"

#include <stdbool.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "sdkconfig.h"

#include "class/hid/hid_device.h"

#include "app_log.h"
#include "kvm_proto.h"
#include "mode.h"
#include "usb_descriptors.h"

/* HID IN 端点就绪的最长等待（ms）：键盘端点 10 ms、鼠标端点 8 ms 轮询一次，
 * 50 ms 足以等到主机取走上一份报告。有界等待避免丢键盘报告（丢上报会卡键），
 * 同时不会把 UART 解析饿死。 */
#define HID_READY_TIMEOUT_MS    (50)

/* 编译期锁死"协议 PAYLOAD 长度"与"HID 报告体长度"的对应关系：
 * 任何一侧单独改动（例如给描述符加字段却忘了改协议实现）都会在这里直接编译失败。 */
_Static_assert(HID_KEYBOARD_REPORT_LEN == KVM_PAYLOAD_LEN_KEYBOARD,
               "boot keyboard report must match KEYBOARD payload");
_Static_assert(HID_MOUSE_REPORT_LEN_RELATIVE == (KVM_PAYLOAD_LEN_MOUSE_REL + 1),
               "relative mouse report (incl. Report ID) must match MOUSE_REL payload");
_Static_assert(HID_MOUSE_REPORT_LEN_ABSOLUTE == (KVM_PAYLOAD_LEN_MOUSE_ABS + 1),
               "absolute mouse report (incl. Report ID) must match MOUSE_ABS payload");

/* 目标机键盘锁定状态缓存（§11.5）：bit0..bit4 为 Num/Caps/Scroll/Compose/Kana，
 * bit7 为 valid（1 = 已收到过 SET_REPORT）。上电为 0（valid=0，状态未知）。
 * 由 tud_hid_set_report_cb() 在 TinyUSB 任务里写，由分发表在 uart2cdc 任务里读，
 * 单字节读写天然原子，故只加 volatile 即可。 */
static volatile uint8_t s_kbd_state = 0;

/* GET HID REPORT DESCRIPTOR：按 instance 返回各自的报告描述符，指针必须长期有效 */
uint8_t const *tud_hid_descriptor_report_cb(uint8_t instance)
{
    switch (instance) {
    case HID_INSTANCE_KEYBOARD:
        return hid_report_descriptor;
    case HID_INSTANCE_MOUSE:
        return hid_report_descriptor_mouse;
    default:
        return NULL;
    }
}

/* GET_REPORT：两个实例都没有可供主机读取的输入报告缓存，返回 0 让协议栈 STALL */
uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id,
                               hid_report_type_t report_type,
                               uint8_t *buffer, uint16_t reqlen)
{
    (void)instance;
    (void)report_id;
    (void)report_type;
    (void)buffer;
    (void)reqlen;

    /* 两个实例都没有可供主机读取的输入报告缓存，返回 0 让协议栈 STALL */
    return 0;
}

/* SET_REPORT / OUT 端点：按 instance 分支。键盘只更新内部缓存（§11.5），
 * 绝不回发任何东西（§3.2：禁止异步推送）。 */
void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id,
                           hid_report_type_t report_type,
                           uint8_t const *buffer, uint16_t bufsize)
{
    (void)report_id;

    switch (instance) {
    case HID_INSTANCE_KEYBOARD:
        /* 唯一来源是目标机的 LED 输出报告（Boot 键盘为 1 字节，bit0..4 五种指示）。
         * 缓存内容 = 指示位 + valid 位；查询时才回复，此处不发任何帧。 */
        if ((report_type == HID_REPORT_TYPE_OUTPUT) && (buffer != NULL) && (bufsize > 0)) {
            s_kbd_state = (uint8_t)((buffer[0] & 0x1Fu) | KVM_KBD_STATE_VALID);
        }
        break;
    case HID_INSTANCE_MOUSE:
        /* 鼠标没有 OUT 报告（无 LED），忽略。 */
        break;
    default:
        break;
    }
}

uint8_t hid_kbd_state(void)
{
    return s_kbd_state;
}

/**
 * @brief 有界等待指定 HID 实例的 IN 端点空闲（主机已取走上一份报告）
 *
 * 多实例场景必须用 tud_hid_n_ready(instance)：tud_hid_ready() 只是 instance 0
 * 的便捷封装，用错会一直等键盘端点。
 */
static bool hid_ready_wait(uint8_t instance)
{
    for (int waited = 0; waited <= HID_READY_TIMEOUT_MS; waited++) {
        if (tud_hid_n_ready(instance)) {
            return true;
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    return false;
}

void hid_emit_keyboard(uint8_t modifier, const uint8_t keycode[6])
{
    if (!mode_is_control()) {
        return;                                  /* §4.1：PASSTHROUGH 不发任何报告 */
    }

    uint8_t keys[6];                             /* 该 API 的 keycode 形参不是 const */
    memcpy(keys, keycode, sizeof(keys));

    if (!hid_ready_wait(HID_INSTANCE_KEYBOARD)) {
        APP_LOGW("kbd IN endpoint busy > %d ms, report dropped", HID_READY_TIMEOUT_MS);
        return;
    }
    if (!tud_hid_n_keyboard_report(HID_INSTANCE_KEYBOARD, 0, modifier, keys)) {
        APP_LOGW("kbd report rejected: mod=0x%02X key0=0x%02X", modifier, keys[0]);
    }
}

void hid_emit_mouse(uint8_t report_id, const uint8_t *body, size_t len)
{
    if (!mode_is_control()) {
        return;
    }
    if (!hid_ready_wait(HID_INSTANCE_MOUSE)) {
        APP_LOGW("mouse IN endpoint busy > %d ms, report dropped", HID_READY_TIMEOUT_MS);
        return;
    }
    if (!tud_hid_n_report(HID_INSTANCE_MOUSE, report_id, body, (uint16_t)len)) {
        APP_LOGW("mouse report rejected: id=%u len=%u", (unsigned)report_id, (unsigned)len);
    }
}