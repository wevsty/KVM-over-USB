/*
 * PASSTHROUGH / CONTROL 模式状态实现（docs/PROTOCOL.md §4）。
 *
 * SPDX-License-Identifier: MIT
 */

#include "mode.h"

/* 当前模式：唯一入口是分发表里的 ENTER_CONTROL / EXIT_CONTROL（协议帧驱动）。
 * 单字节状态，分发任务写、CDC 透传与 HID 发送读，天然原子，无需加锁。 */
static app_mode_t s_mode = MODE_PASSTHROUGH;

app_mode_t mode_get(void)
{
    return s_mode;
}

void mode_set(app_mode_t mode)
{
    s_mode = mode;
}

bool mode_is_control(void)
{
    return s_mode == MODE_CONTROL;
}