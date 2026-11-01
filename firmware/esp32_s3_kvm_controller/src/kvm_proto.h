/*
 * KVM 协议常量（依据 docs/PROTOCOL.md v1.4）：帧结构、TYPE、PAYLOAD 长度、超时。
 * 协议已冻结（AGENTS.md 第 7 条）：数值禁止擅自修改。
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */

#pragma once

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ===== 帧结构（§5.1）=====
 * MAGIC(8) + VERSION(1) + TYPE(1) + LENGTH(2, LE) + PAYLOAD(N) + FNV1A32(4, LE)
 * 总长 = 16 + N
 */
#define KVM_MAGIC_LEN               (8u)
#define KVM_VERSION                 (0x01u)
#define KVM_HEADER_LEN              (12u)   /* MAGIC + VERSION + TYPE + LENGTH */
#define KVM_CHECK_LEN               (4u)    /* FNV1A32 字段长度 */
#define KVM_MAX_PAYLOAD             (1024u) /* §5.3 */
#define KVM_MAX_FRAME               (KVM_HEADER_LEN + KVM_MAX_PAYLOAD + KVM_CHECK_LEN) /* 1040 */

/* FNV 覆盖范围（§7.2）：从 VERSION（偏移 8）到 PAYLOAD 最后一字节，
 * 即 frame[8] .. frame[11 + N]，长度 = 4 + N。不含 MAGIC 与校验字段本身。 */
#define KVM_FNV_RANGE_OFFSET        (KVM_MAGIC_LEN)
#define KVM_FNV_FIXED_LEN           (4u)    /* VERSION + TYPE + LENGTH */

/* 帧内超时（§13.5）：HEADER/PAYLOAD/CHECK 状态 100 ms 无新字节 → A 类失败 */
#define KVM_FRAME_TIMEOUT_MS        (100u)

/* FNV-1a-32 的参数与算法实现见 fnv1a32.h / fnv1a32.c（与协议无关的独立模块） */

/* ===== TYPE 总表（§6）===== */
typedef enum {
    KVM_TYPE_ENTER_CONTROL          = 0x01, /* 上位机→控制器 */
    KVM_TYPE_EXIT_CONTROL           = 0x02, /* 上位机→控制器 */
    KVM_TYPE_RESET                  = 0x03, /* 上位机→控制器（整机重启，§4.5） */
    KVM_TYPE_KEYBOARD               = 0x10, /* 上位机→控制器 */
    KVM_TYPE_MOUSE_REL              = 0x11, /* 上位机→控制器 */
    KVM_TYPE_MOUSE_ABS              = 0x12, /* 上位机→控制器 */
    KVM_TYPE_REPORT_KEYBOARD_STATE  = 0x13, /* 控制器→上位机 */
    KVM_TYPE_QUERY_KEYBOARD_STATE   = 0x14, /* 上位机→控制器 */
    KVM_TYPE_PING                   = 0x20, /* 上位机→控制器 */
    KVM_TYPE_PONG                   = 0x21, /* 控制器→上位机 */
} kvm_type_t;

/* ===== 各 TYPE 的固定 PAYLOAD 长度（§6 / §8~§12）===== */
#define KVM_PAYLOAD_LEN_ENTER_CONTROL           (0u)
#define KVM_PAYLOAD_LEN_EXIT_CONTROL            (0u)
#define KVM_PAYLOAD_LEN_RESET                   (0u)  /* 无参数：收到即重启（§4.5） */
#define KVM_PAYLOAD_LEN_KEYBOARD                (8u)  /* modifier + reserved + 6 x keycode */
#define KVM_PAYLOAD_LEN_MOUSE_REL               (4u)  /* buttons + dx + dy + wheel */
#define KVM_PAYLOAD_LEN_MOUSE_ABS               (6u)  /* buttons + x(LE16) + y(LE16) + wheel */
#define KVM_PAYLOAD_LEN_REPORT_KEYBOARD_STATE   (1u)
#define KVM_PAYLOAD_LEN_QUERY_KEYBOARD_STATE    (0u)
#define KVM_PAYLOAD_LEN_PING                    (1u)  /* tag */
#define KVM_PAYLOAD_LEN_PONG                    (4u)  /* tag + mode + version + reserved */

/* ===== REPORT_KEYBOARD_STATE 位定义（§11.3）===== */
#define KVM_KBD_STATE_NUM_LOCK      (1u << 0)
#define KVM_KBD_STATE_CAPS_LOCK     (1u << 1)
#define KVM_KBD_STATE_SCROLL_LOCK   (1u << 2)
#define KVM_KBD_STATE_COMPOSE       (1u << 3)
#define KVM_KBD_STATE_KANA          (1u << 4)
#define KVM_KBD_STATE_VALID         (1u << 7)  /* 1 = 已从 SET_REPORT 获取 */

/* ===== PONG 的 mode 字段（§12.2）===== */
#define KVM_MODE_PASSTHROUGH        (0u)
#define KVM_MODE_CONTROL            (1u)

/* 协议帧 MAGIC 实体：4B 56 4D 00 A5 5A C3 3C，定义在 kvm_frame.c */
extern const uint8_t kvm_proto_frame_magic[KVM_MAGIC_LEN];

#ifdef __cplusplus
}
#endif