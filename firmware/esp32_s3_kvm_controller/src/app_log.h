/*
 * 全工程共用的日志开关与宏。
 * 发布态两个开关必须为 0：COM5 与协议通道共用 UART0（docs/PROTOCOL.md §16.1）。
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include "esp_log.h"

/* 所有模块共用同一 TAG，日志行前缀保持 "kvm" 不变 */
#define APP_LOG_TAG             "kvm"

/* 协议/透传详细日志。1 = 打印；0 = 静音（符合 docs/PROTOCOL.md §16.1）。 */
#define APP_PROTO_LOG           (0)

/* 逐条 HID 报告日志（键盘/鼠标每收到一帧打一行）。发布态为 0，理由同上；
 * 鼠标连续移动时日志量很大，保持 1 会明显挤占 UART 带宽。 */
#define APP_HID_REPORT_LOG      (0)

#if APP_PROTO_LOG
#define APP_LOGI(fmt, ...)      ESP_LOGI(APP_LOG_TAG, fmt, ##__VA_ARGS__)
#define APP_LOGW(fmt, ...)      ESP_LOGW(APP_LOG_TAG, fmt, ##__VA_ARGS__)
#else
#define APP_LOGI(fmt, ...)      do { } while (0)
#define APP_LOGW(fmt, ...)      do { } while (0)
#endif

#if APP_PROTO_LOG && APP_HID_REPORT_LOG
#define APP_HID_LOGI(fmt, ...)  ESP_LOGI(APP_LOG_TAG, fmt, ##__VA_ARGS__)
#else
#define APP_HID_LOGI(fmt, ...)  do { } while (0)
#endif