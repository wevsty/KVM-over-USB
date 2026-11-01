/*
 * PASSTHROUGH / CONTROL 模式状态（docs/PROTOCOL.md §4）。
 * 只保存当前模式；切换由分发表驱动，本模块不做任何自动切换。
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */

#pragma once

#include <stdbool.h>

#include "kvm_proto.h"

/* 两种模式（§4.1）。枚举值直接取协议的 PONG.mode 字段值（§12.2），回 PONG 时不用再映射。 */
typedef enum {
    MODE_PASSTHROUGH = KVM_MODE_PASSTHROUGH,   /* 0：上电默认 */
    MODE_CONTROL     = KVM_MODE_CONTROL,       /* 1 */
} app_mode_t;

/**
 * @brief 当前模式
 */
app_mode_t mode_get(void);

/**
 * @brief 设置模式（调用方各自负责打切换日志；本函数不发任何帧、不碰 CDC/UART）
 */
void mode_set(app_mode_t mode);

/**
 * @brief 是否处于 CONTROL（最常见的判断，省掉一处处 == MODE_CONTROL）
 */
bool mode_is_control(void);