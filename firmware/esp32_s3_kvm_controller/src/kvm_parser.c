/*
 * 流式帧解析器实现（docs/PROTOCOL.md §13.3 / §13.5）。
 * 滑窗 + MAGIC 扫描 + A/B 类判定；两个出口由 kvm_parser_init() 注入。
 *
 * SPDX-License-Identifier: MIT
 */

#include "kvm_parser.h"

#include <string.h>

#include "esp_timer.h"

#include "app_log.h"
#include "fnv1a32.h"
#include "kvm_frame.h"
#include "kvm_proto.h"

/* 滑窗缓冲：上限 KVM_MAX_FRAME(1040)。parser_run() 每次返回后窗口至少留 1 字节空位，
 * 因此 kvm_parser_feed() 追加字节永远不会溢出（见该函数注释）。 */
static uint8_t s_win[KVM_MAX_FRAME];
static size_t s_win_len = 0;
/* 最近一次收到字节的时刻（us）：帧内超时基准 */
static int64_t s_win_last_rx_us = 0;

/* 两个出口：由 kvm_parser_init() 注入；未注入时对应数据直接丢弃 */
static kvm_parser_byte_sink_t s_byte_sink = NULL;
static kvm_parser_frame_sink_t s_frame_sink = NULL;

void kvm_parser_init(kvm_parser_byte_sink_t on_non_frame, kvm_parser_frame_sink_t on_frame)
{
    s_byte_sink = on_non_frame;
    s_frame_sink = on_frame;
    s_win_len = 0;
    s_win_last_rx_us = 0;
}

/**
 * @brief A 类出口：这些字节不构成帧（§13.4）
 */
static void parser_emit_non_frame(const uint8_t *p, size_t n)
{
    if ((s_byte_sink != NULL) && (n > 0)) {
        s_byte_sink(p, n);
    }
}

/**
 * @brief 帧出口：帧成立，交分发表（B 类丢弃时不回退转发）
 */
static void parser_emit_frame(uint8_t type, const uint8_t *payload, uint16_t len)
{
    if (s_frame_sink != NULL) {
        s_frame_sink(type, payload, len);
    }
}

/**
 * @brief buf 前 avail 字节与 MAGIC 的公共前缀长度（上限 KVM_MAGIC_LEN）
 */
static size_t parser_magic_prefix_len(const uint8_t *buf, size_t avail)
{
    size_t k = 0;

    while ((k < avail) && (k < KVM_MAGIC_LEN) && (buf[k] == kvm_proto_frame_magic[k])) {
        k++;
    }
    return k;
}

/**
 * @brief 滑窗前移 n 字节（n >= s_win_len 时直接清空）
 */
static void parser_win_shift(size_t n)
{
    if (n >= s_win_len) {
        s_win_len = 0;
        return;
    }
    memmove(s_win, &s_win[n], s_win_len - n);
    s_win_len -= n;
}

/**
 * @brief 主循环：把窗口内能判定的字节全部处理掉（§13.3 parse_loop）
 *
 * 返回时窗口里只剩"还不完整的候选帧"：
 *   - 纯 MAGIC 前缀（长度 < 8）：SCAN 态，等待更多字节，无超时；
 *   - MAGIC 已完整但头部未收齐，或头部已收齐但 PAYLOAD/CHECK 未到齐：
 *     HEADER/PAYLOAD/CHECK 态，受 100 ms 帧内超时约束。
 */
static void parser_run(void)
{
    for (;;) {
        const size_t avail = s_win_len;
        if (avail == 0) {
            return;
        }

        /* 1) MAGIC 前缀匹配 */
        const size_t k = parser_magic_prefix_len(s_win, avail);
        if (k < KVM_MAGIC_LEN) {
            if ((k == avail) && (avail < KVM_MAGIC_LEN)) {
                return;                     /* 全是前缀，等待更多字节 */
            }
            /* s_win[k] 破坏了前缀：前 k 字节确定不是帧；k == 0 说明 s_win[0] 本身不是 MAGIC[0]。
             * MAGIC 无前缀自重叠（§5.4），所以这些字节整段前移不会漏掉嵌套的真实帧起点。 */
            const size_t n = (k > 0) ? k : 1;
            parser_emit_non_frame(s_win, n);
            parser_win_shift(n);
            continue;
        }

        /* 2) MAGIC 完整：检查 VERSION / TYPE / LENGTH */
        if (avail < KVM_HEADER_LEN) {
            return;                         /* 等待 VERSION/TYPE/LENGTH */
        }

        const uint8_t ver = s_win[8];
        const uint8_t type = s_win[9];
        const uint16_t len = read_le16_bytes(&s_win[10]);

        if ((ver != KVM_VERSION) || (len > KVM_MAX_PAYLOAD)) {
            APP_LOGW("frame header rejected: ver=0x%02X len=%u -> 1 byte to passthrough (A class)",
                     ver, (unsigned)len);
            parser_emit_non_frame(s_win, 1);
            parser_win_shift(1);
            continue;
        }

        /* 3) 等待整帧到齐：MAGIC + VERSION + TYPE + LENGTH + PAYLOAD + FNV */
        const size_t total = (size_t)KVM_HEADER_LEN + len + KVM_CHECK_LEN;
        if (avail < total) {
            return;
        }

        /* 4) FNV 校验（范围 frame[8] .. frame[11 + N]，§7.2） */
        const uint32_t calc = fnv1a32(&s_win[KVM_FNV_RANGE_OFFSET],
                                      (size_t)KVM_FNV_FIXED_LEN + len);
        const uint32_t recv = read_le32_bytes(&s_win[KVM_HEADER_LEN + len]);

        if (calc != recv) {
            APP_LOGW("frame fnv mismatch: type=0x%02X len=%u calc=0x%08X recv=0x%08X "
                     "-> 1 byte to passthrough (A class)",
                     type, (unsigned)len, (unsigned)calc, (unsigned)recv);
            parser_emit_non_frame(s_win, 1);
            parser_win_shift(1);
            continue;
        }

        /* 5) 帧成立：交帧出口，整帧移出窗口（B 类丢弃时不回退转发） */
        parser_emit_frame(type, &s_win[KVM_HEADER_LEN], len);
        parser_win_shift(total);
    }
}

void kvm_parser_feed(const uint8_t *data, size_t len)
{
    size_t off = 0;

    while (off < len) {
        size_t space = sizeof(s_win) - s_win_len;
        if (space == 0) {
            APP_LOGW("parser window full (%u bytes), flushing as A class",
                     (unsigned)s_win_len);
            parser_emit_non_frame(s_win, s_win_len);
            s_win_len = 0;
            space = sizeof(s_win);
        }

        size_t n = len - off;
        if (n > space) {
            n = space;
        }
        memcpy(&s_win[s_win_len], &data[off], n);
        s_win_len += n;
        off += n;
        s_win_last_rx_us = esp_timer_get_time();

        parser_run();
    }
}

void kvm_parser_poll(void)
{
    if (s_win_len < KVM_MAGIC_LEN) {
        return;                             /* SCAN 态，无超时 */
    }

    const int64_t now_us = esp_timer_get_time();
    if ((now_us - s_win_last_rx_us) < ((int64_t)KVM_FRAME_TIMEOUT_MS * 1000)) {
        return;
    }

    APP_LOGW("frame timeout %u ms: %u buffered bytes -> passthrough, back to SCAN",
             (unsigned)KVM_FRAME_TIMEOUT_MS, (unsigned)s_win_len);
    parser_emit_non_frame(s_win, s_win_len);
    s_win_len = 0;
}