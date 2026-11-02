/*
 * UART0（GPIO43/44 → CH343 → COM5）底层接口：初始化、读、写、TX 排空。
 * 上层只通过本头文件访问 UART，不直接使用 driver/uart.h。
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

/* 波特率：与 docs/PROTOCOL.md §2 物理层一致（115200 8N1，无流控） */
#define UART_BRIDGE_BAUD_RATE       (115200)

/* 单次读取的建议长度（字节）：调用方按此开栈上缓冲即可 */
#define UART_BRIDGE_RX_CHUNK        (256)

/* 无数据时的等待时间（ms）：只让读任务周期性醒来，不做任何主动输出 */
#define UART_BRIDGE_READ_TIMEOUT_MS (20)

/**
 * @brief 安装并配置 UART0：115200 8N1，无流控
 *
 * @return ESP_OK 成功，其余为 esp_err_t 错误码（由调用方 ESP_ERROR_CHECK 处理）
 */
esp_err_t uart_bridge_init(void);

/**
 * @brief 向 UART TX 写一段字节（阻塞到全部写入驱动缓冲）
 *
 * @param data 数据指针，NULL 或 len == 0 时直接返回 0
 * @param len  字节数
 * @return 实际写入字节数；< 0 表示错误
 */
int uart_bridge_write(const uint8_t *data, size_t len);

/**
 * @brief 从 UART RX 读一段字节
 *
 * @param data       输出缓冲
 * @param len        最多读取的字节数
 * @param timeout_ms 无数据时的等待时间（ms），0 表示不等待
 * @return 实际读到的字节数；< 0 表示错误
 */
int uart_bridge_read(uint8_t *data, size_t len, int timeout_ms);

/**
 * @brief 等待 UART TX 发完（复位前用，避免把正在发送的帧切断）
 *
 * @param timeout_ms 最长等待时间（ms）
 * @return true 已发完；false 超时或出错
 */
bool uart_bridge_wait_tx_done(int timeout_ms);