/*
 * 协议帧组帧实现（docs/PROTOCOL.md §5.1 / §7）。
 *
 * SPDX-License-Identifier: MIT
 */

#include "kvm_frame.h"

#include <string.h>

#include "fnv1a32.h"

const uint8_t kvm_proto_frame_magic[KVM_MAGIC_LEN] = { 0x4B, 0x56, 0x4D, 0x00,
                                                       0xA5, 0x5A, 0xC3, 0x3C };

size_t kvm_frame_encode(uint8_t *out, size_t out_size, uint8_t type,
                        const uint8_t *payload, uint16_t payload_len)
{
    if ((out == NULL) || (payload_len > KVM_MAX_PAYLOAD)) {
        return 0;
    }
    if ((payload_len > 0) && (payload == NULL)) {
        return 0;
    }

    const size_t total = (size_t)KVM_HEADER_LEN + payload_len + KVM_CHECK_LEN;
    if (out_size < total) {
        return 0;
    }

    memcpy(out, kvm_proto_frame_magic, KVM_MAGIC_LEN);
    out[8] = KVM_VERSION;
    out[9] = type;
    write_le16_bytes(&out[10], payload_len);
    if (payload_len > 0) {
        memcpy(&out[KVM_HEADER_LEN], payload, payload_len);
    }

    /* 校验范围 VERSION..PAYLOAD 末尾，不含 MAGIC 与校验字段（§7.2） */
    const uint32_t fnv = fnv1a32(&out[KVM_FNV_RANGE_OFFSET],
                                 (size_t)KVM_FNV_FIXED_LEN + payload_len);
    write_le32_bytes(&out[KVM_HEADER_LEN + payload_len], fnv);
    return total;
}