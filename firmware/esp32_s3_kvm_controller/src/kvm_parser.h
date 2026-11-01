/*
 * 流式帧解析器接口（docs/PROTOCOL.md §13.3 / §13.5）。
 * 只判定"是不是帧"，不认识模式机、CDC 与分发表。
 * feed() / poll() 必须在同一任务里调用（内部不加锁）。
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */

#pragma once

#include <stddef.h>
#include <stdint.h>

/* A 类字节出口：这些字节不构成帧，按透传规则处理 */
typedef void (*kvm_parser_byte_sink_t)(const uint8_t *data, size_t len);

/* 帧出口：校验通过的完整帧，payload 指向解析器内部缓冲，回调返回后即失效 */
typedef void (*kvm_parser_frame_sink_t)(uint8_t type, const uint8_t *payload, uint16_t len);

/**
 * @brief 注册两个出口（在启动收发任务之前调用；未注册的出口对应数据直接丢弃）
 */
void kvm_parser_init(kvm_parser_byte_sink_t on_non_frame, kvm_parser_frame_sink_t on_frame);

/**
 * @brief 喂入一段 UART 收到的字节，内部循环把能判定的部分处理完
 *
 * 返回时滑窗里只剩"还不完整的候选帧"，因此永远有空位接收新字节。
 */
void kvm_parser_feed(const uint8_t *data, size_t len);

/**
 * @brief 帧内超时判定（§13.5）：必须被周期性调用
 *
 * 只有进帧状态（已收满 MAGIC）才超时；纯 MAGIC 前缀（SCAN 态）无超时。
 */
void kvm_parser_poll(void);