/*
 * USB HID 接口：键盘 LED 状态缓存 + 键盘/鼠标报告发送。
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */

#pragma once

#include <stddef.h>
#include <stdint.h>

/**
 * @brief 缓存的键盘锁定状态（§11.5）
 *
 * bit0..bit4 = Num/Caps/Scroll/Compose/Kana，bit7 = valid（1 = 已收到过 SET_REPORT）。
 * 上电为 0（valid = 0，状态未知）。只在收到 QUERY_KEYBOARD_STATE 时读取，从不主动推送。
 */
uint8_t hid_kbd_state(void);

/**
 * @brief 发送键盘 Boot 报告（8 字节：modifier + reserved(0) + keycode[6]）
 *
 * 仅在 CONTROL 下真正发送（其余模式直接返回）；IN 端点忙时有界等待，超时丢报告并告警。
 */
void hid_emit_keyboard(uint8_t modifier, const uint8_t keycode[6]);

/**
 * @brief 发送鼠标报告（body 不含 Report ID，由 tud_hid_n_report 自动前置）
 *
 * Report ID 1 的报告体 4 字节（buttons/dx/dy/wheel），
 * Report ID 2 的报告体 6 字节（buttons/x/y/wheel），均与描述符逐字段一致。
 */
void hid_emit_mouse(uint8_t report_id, const uint8_t *body, size_t len);