/*
 * FNV-1a-32 哈希（参数见 docs/PROTOCOL.md §7.1）。
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define FNV1A32_OFFSET_BASIS    (0x811C9DC5u)
#define FNV1A32_PRIME           (0x01000193u)

/**
 * @brief 对一段数据计算 FNV-1a-32
 *
 * @param data 数据起始地址，len 为 0 时可为 NULL
 * @param len  字节数
 * @return 32 位哈希值
 */
uint32_t fnv1a32(const uint8_t *data, size_t len);

#ifdef __cplusplus
}
#endif