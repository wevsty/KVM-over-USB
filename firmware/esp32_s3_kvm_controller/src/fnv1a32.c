/*
 * FNV-1a-32 实现（docs/PROTOCOL.md §7.3）。
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */

#include "fnv1a32.h"

uint32_t fnv1a32(const uint8_t *data, size_t len)
{
    uint32_t hash = FNV1A32_OFFSET_BASIS;

    if (data == NULL) {
        return hash;
    }

    for (size_t i = 0; i < len; i++) {
        hash ^= data[i];
        hash *= FNV1A32_PRIME;   /* uint32_t 自然溢出回绕，不做额外掩码 */
    }
    return hash;
}