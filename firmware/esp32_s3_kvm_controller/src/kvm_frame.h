/*
 * 协议帧组帧接口 + 小端读写辅助（docs/PROTOCOL.md §5 / §7.1）。
 * 只处理完整帧；流式拼装在 kvm_parser.c。
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stddef.h>
#include <stdint.h>

#include "kvm_proto.h"

/* 协议帧 MAGIC：4B 56 4D 00 A5 5A C3 3C（§5.2；第 4 字节 0x00 保证无前缀自重叠，§5.4）。
 * 定义在 kvm_frame.c：它守的是全部协议帧，不只 ENTER_CONTROL。 */
extern const uint8_t kvm_proto_frame_magic[KVM_MAGIC_LEN];

/* 小端读写的唯一定义处：协议所有多字节整数一律小端（§2）。
 * 放在头文件里用 static inline：解析器要按帧读 LENGTH / FNV，跨 TU 调用没有收益。 */
static inline uint16_t read_le16_bytes(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static inline uint32_t read_le32_bytes(const uint8_t *p)
{
    return (uint32_t)p[0] |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static inline void write_le16_bytes(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)(v & 0xFF);
    p[1] = (uint8_t)((v >> 8) & 0xFF);
}

static inline void write_le32_bytes(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v & 0xFF);
    p[1] = (uint8_t)((v >> 8) & 0xFF);
    p[2] = (uint8_t)((v >> 16) & 0xFF);
    p[3] = (uint8_t)((v >> 24) & 0xFF);
}

/**
 * @brief 组一帧（§5.1）：MAGIC + VERSION + TYPE + LENGTH + PAYLOAD + FNV
 *
 * @param out          输出缓冲
 * @param out_size     输出缓冲容量
 * @param type         TYPE 枚举值
 * @param payload      PAYLOAD 指针，payload_len 为 0 时可为 NULL
 * @param payload_len  PAYLOAD 长度，> KVM_MAX_PAYLOAD 直接拒绝
 * @return 帧总长（16 + payload_len）；参数非法或缓冲不足返回 0
 */
size_t kvm_frame_encode(uint8_t *out, size_t out_size, uint8_t type,
                        const uint8_t *payload, uint16_t payload_len);