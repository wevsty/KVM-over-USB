# KVM 控制器通信协议规范

**文档版本**：1.4
**协议版本**：0x01
**适用硬件**：ESP32-S3（USB OTG + CH343/CH340/等 UART）

---

## 1. 概述

### 1.1 系统拓扑

```text
控制端(PC/手机)
    │  CH343 UART (COM5)
    ▼
KVM 控制器 (ESP32-S3)
    │  原生 USB OTG (GPIO19/20)
    ▼
目标机 —— 枚举为：HID 键盘 + HID 鼠标 + CDC ACM 串口
```

### 1.2 两条独立链路

| 链路 | 用途 |
|---|---|
| **UART（CH343）** | 本协议唯一通道，控制端 ↔ 控制器 |
| **USB OTG** | 控制器 → 目标机：HID 报告 + CDC 数据 |

控制端**永远只通过 UART** 与控制器通信。

### 1.3 CDC 的定位

CDC 是**给目标机用的**。默认模式下控制器把 UART 数据透明转发给 CDC，
使 putty 等第三方串口工具无需专用上位机即可操作目标机。

---

## 2. 物理层

| 参数 | 值 |
|---|---|
| 波特率 | **115200** |
| 数据位 | 8 |
| 校验 | 无 |
| 停止位 | 1 |
| 流控 | 无 |
| 字节序 | 所有多字节整数一律**小端（little-endian）** |

115200 的选取理由：键鼠帧极小，透传场景为交互式操作，该速率
为绝大多数开发板（含低成本兼容板）与串口工具的默认支持值。

---

## 3. 固件行为准则（规范性）

本节定义整个协议的设计基调，实现时必须遵守。

控制器是**纯粹的反应式设备**：每一帧下行数据都必须是对某一帧上行
请求的直接响应。

### 3.1 允许发送的帧（白名单）

| 下行帧 | 唯一触发条件 |
|---|---|
| `PONG` | 收到 `PING` |
| `REPORT_KEYBOARD_STATE` | 收到 `QUERY_KEYBOARD_STATE` |

**除以上两种，固件不得发送任何帧。**

### 3.2 明确禁止的行为

| 禁止项 | 说明 |
|---|---|
| 上电/复位问候帧 | 不发版本、就绪、横幅类帧 |
| 进入 CONTROL 时主动推送 | 不推送键盘状态、模式通知 |
| 键盘状态变化时异步推送 | SET_REPORT 只更新内部缓存，**不发送** |
| 定时器/心跳帧 | 无周期性输出 |
| 主动退出 CONTROL | 无超时回退、无看门狗式模式复位 |
| 主动停止透传 | 模式只由上行指令改变 |
| ERROR / NAK 帧 | 无响应即代表失败 |

### 3.3 允许的内部行为（不属于"主动操作"）

- 缓存目标机最新键盘状态（供查询时返回）
- 更新内部模式标志
- 调试构建下输出运行时日志（见 16.1）

### 3.4 上行帧触发的完整响应表

| 上行帧 | 下行响应 |
|---|---|
| `ENTER_CONTROL` | **无** |
| `EXIT_CONTROL` | **无** |
| `RESET` | **无**（重启前不发任何帧，§4.5） |
| `KEYBOARD` | **无** |
| `MOUSE_REL` | **无** |
| `MOUSE_ABS` | **无** |
| `PING` | `PONG` |
| `QUERY_KEYBOARD_STATE` | `REPORT_KEYBOARD_STATE` |
| 未知/非法帧 | **无**（静默丢弃） |

---

## 4. 模式与状态机

### 4.1 两个模式

| 模式 | UART RX | UART TX | CDC | HID |
|---|---|---|---|---|
| **PASSTHROUGH**（上电默认） | 扫描帧头；非帧数据转发 CDC | 只转发 CDC 数据，**禁止任何协议帧** | 双向工作 | 已枚举，**不发报告** |
| **CONTROL** | 只解析协议帧 | 只发下行响应帧 | **完全停止**（接收丢弃） | 按帧发送报告 |

### 4.2 状态转换

```text
         上电 → PASSTHROUGH
                  │  ENTER_CONTROL（帧校验通过）
                  ▼
              CONTROL
                  │  EXIT_CONTROL（帧校验通过）
                  ▼
             PASSTHROUGH
```

### 4.3 转换语义

| 当前模式 | 收到帧 | 行为 |
|---|---|---|
| PASSTHROUGH | `ENTER_CONTROL` | 切换到 CONTROL |
| PASSTHROUGH | 其他任何合法帧 | **整帧丢弃**，保持 PASSTHROUGH（B 类，见 13.4） |
| CONTROL | `ENTER_CONTROL` | **幂等**，保持 CONTROL，无副作用 |
| CONTROL | `EXIT_CONTROL` | 切回 PASSTHROUGH |
| CONTROL | 其他 | 按 3.4 处理 |

### 4.4 USB 枚举约束

- USB 设备在**上电时一次性完成枚举**（键盘 + 鼠标 + CDC 同时出现）。
- 模式切换**不触发重新枚举**，目标机不会看到设备断开重连。
- 因此在 BIOS 中切换模式，键鼠不会消失。

### 4.5 RESET（TYPE `0x03`）

**语义**：让控制器**整机重启**（`esp_restart()`）。RAM 全部重建，USB 设备重新枚举。

与 `EXIT_CONTROL` 的分工必须分清：

| 项目 | `EXIT_CONTROL` | `RESET` |
|---|---|---|
| 作用 | 只切换模式 | 整机重启 |
| USB 连接 | 不断开（§4.4） | **断开并重新枚举** |
| 目标机侧 CDC 句柄 | 保持有效 | **必然失效**，需重新打开 |
| 键盘状态缓存 | 保持 | 清空（`valid = 0`，§11.5） |
| 适用场景 | 正常收尾 | 固件异常 / 需要清空全部状态 |

**`RESET` 不得作为 `EXIT_CONTROL` 的替代品**：正常结束会话一律用
`EXIT_CONTROL`，只有确实需要重启控制器时才用 `RESET`。

**请求**：TYPE `0x03`，PAYLOAD 0 字节，帧长固定 16 字节。**无任何下行响应**
（§3.1 白名单不变）。

**触发条件与处理**：

| 当前模式 | PAYLOAD 长度 | 行为 |
|---|---|---|
| CONTROL | 0 | 先等 UART TX 发完（≤ 50 ms），再 `esp_restart()` |
| CONTROL | ≠ 0 | B 类：整帧丢弃，**绝不重启**（§15.2） |
| PASSTHROUGH | 任意 | B 类：整帧丢弃，**绝不重启**（§4.3） |

PASSTHROUGH 下不生效是 §4.3「PASSTHROUGH 下只有 `ENTER_CONTROL` 有效」的
直接推论：上位机必须先进入 CONTROL 再发 `RESET`。

**复位后的状态**：

| 项 | 复位后的值 |
|---|---|
| 模式 | `PASSTHROUGH`（上电默认，§4.1） |
| 键盘状态缓存 | 全 0，`valid = 0`（§11.5） |
| USB | 控制器重新枚举；§4.4 的「不重枚举」不适用（这是重启，不是模式切换） |
| UART | bootloader 输出上电日志，上位机解析器靠 MAGIC 跳过（§16.1） |

**COM5 不会消失**：它是 CH343 桥出来的串口，与 ESP32-S3 是两颗独立芯片。
复位期间上位机会在该串口上看到 bootloader 文案，随后恢复正常。

---

## 5. 帧格式

### 5.1 总览

```text
偏移   长度   字段
0      8      MAGIC
8      1      VERSION
9      1      TYPE
10     2      LENGTH        (PAYLOAD 长度，小端)
12     N      PAYLOAD
12+N   4      FNV1A32       (小端)
总长 = 16 + N
```

### 5.2 字段定义

| 字段 | 长度 | 值 / 说明 |
|---|---|---|
| **MAGIC** | 8 | 固定 `4B 56 4D 00 A5 5A C3 3C` |
| **VERSION** | 1 | 固定 `0x01` |
| **TYPE** | 1 | 见第 6 节 |
| **LENGTH** | 2 | PAYLOAD 字节数，小端，最大 1024 |
| **PAYLOAD** | N | 命令数据，可为 0 |
| **FNV1A32** | 4 | 校验值，小端 |

### 5.3 长度限制

| 项 | 值 |
|---|---|
| MAX_PAYLOAD | 1024 字节 |
| MAX_FRAME | 1040 字节 |
| LENGTH > MAX_PAYLOAD | 按 A 类失败处理（见 13.4） |

### 5.4 MAGIC 选取理由

- 8 字节整匹配，随机文本命中概率约 2^-64。
- 第 4 字节为 `0x00`，保证**无前缀自重叠**：任意前缀都不等于任意后缀，
  因此解析失败时"已匹配前缀"可整体前移，不会漏掉嵌套帧起点。
- 前 3 字节 ASCII 为 `KVM`，便于在十六进制查看器中定位。

---

## 6. 命令类型总表

| TYPE | 名称 | 方向 | PAYLOAD | 说明 |
|---|---|---|---|---|
| `0x01` | `ENTER_CONTROL` | 上位机→控制器 | 0 | 进入 CONTROL 模式 |
| `0x02` | `EXIT_CONTROL` | 上位机→控制器 | 0 | 返回 PASSTHROUGH 模式 |
| `0x03` | `RESET` | 上位机→控制器 | 0 | 整机重启（见 §4.5） |
| `0x10` | `KEYBOARD` | 上位机→控制器 | 8 | 键盘 HID 报告 |
| `0x11` | `MOUSE_REL` | 上位机→控制器 | 4 | 相对坐标鼠标 |
| `0x12` | `MOUSE_ABS` | 上位机→控制器 | 6 | 绝对坐标鼠标 |
| `0x13` | `REPORT_KEYBOARD_STATE` | 控制器→上位机 | 1 | 键盘状态响应 |
| `0x14` | `QUERY_KEYBOARD_STATE` | 上位机→控制器 | 0 | 查询键盘状态 |
| `0x20` | `PING` | 上位机→控制器 | 1 | 存活/模式/版本探测 |
| `0x21` | `PONG` | 控制器→上位机 | 4 | PING 响应 |

上行帧与下行帧使用**完全相同的帧结构**，仅 TYPE 与方向不同。
上位机需同时实现发送端与接收端解析器。

---

## 7. 校验算法：FNV-1a-32

### 7.1 参数

| 参数 | 值 |
|---|---|
| 算法 | FNV-1a 32-bit |
| Offset basis | `0x811C9DC5` |
| Prime | `0x01000193` |
| 运算宽度 | 32 位无符号，自然溢出回绕 |

### 7.2 计算范围

从 **VERSION（偏移 8）** 到 **PAYLOAD 最后一字节**：

```text
frame[8] .. frame[11 + N]
```

包含 VERSION、TYPE、LENGTH、PAYLOAD；**不包含 MAGIC 与校验字段本身**。

### 7.3 参考实现

```c
uint32_t fnv1a32(const uint8_t *data, size_t len)
{
    uint32_t h = 0x811C9DC5u;
    for (size_t i = 0; i < len; i++) {
        h ^= data[i];
        h *= 0x01000193u;
    }
    return h;
}
```

校验字段以**小端 4 字节**写入帧尾。

### 7.4 选用理由

FNV-1a-32 无多项式反射、初值、异或输出等可选参数，
跨语言实现结果一致，不存在 CRC 变种歧义。

---

## 8. KEYBOARD（TYPE 0x10）

PAYLOAD 固定 8 字节，直接对应 **USB HID Boot Protocol** 键盘报告。

| 偏移 | 字段 | 说明 |
|---|---|---|
| 0 | Modifier | 修饰键位图 |
| 1 | Reserved | 固定 `0x00` |
| 2~7 | Keycode[6] | HID Usage ID（Page 0x07），最多 6 键 |

### 8.1 Modifier 位定义

| Bit | 键 |
|---|---|
| 0 | Left Ctrl |
| 1 | Left Shift |
| 2 | Left Alt |
| 3 | Left GUI（Win / Command） |
| 4 | Right Ctrl |
| 5 | Right Shift |
| 6 | Right Alt |
| 7 | Right GUI |

### 8.2 常用组合键

| 目标 | Modifier | Keycode |
|---|---|---|
| Ctrl+Alt+Del | `0x05` | `0x4C` |
| Alt+Tab | `0x04` | `0x2B` |
| Win | `0x08` | 全 `0x00` |
| Ctrl+C | `0x01` | `0x06` |
| Shift+A | `0x02` | `0x04` |

### 8.3 约束

- 仅支持 **6KRO**。BIOS 只支持 Boot Protocol，NKRO 在 BIOS 下不可用。
- 释放全部按键：发送全 `0x00` 的报告。
- 上位机负责生成 HID Usage ID，控制器**不做任何键码翻译**。
- 特殊键（Ctrl+Alt+Del、Alt+Tab、Win）无需控制器特殊处理，
  由上位机组合 Modifier 与 Keycode 实现。

---

## 9. MOUSE_REL（TYPE 0x11）

PAYLOAD 固定 4 字节。

| 偏移 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 0 | Buttons | uint8 | 按键位图 |
| 1 | dx | int8 | 水平位移，右为正 |
| 2 | dy | int8 | 垂直位移，**下为正** |
| 3 | wheel | int8 | 滚轮，**上滚为正** |

### 9.1 Buttons 位定义

| Bit | 键 |
|---|---|
| 0 | 左键 |
| 1 | 右键 |
| 2 | 中键 |
| 3 | 侧键 1（Back） |
| 4 | 侧键 2（Forward） |
| 5~7 | 保留，填 0 |

### 9.2 使用说明

- 这是 **BIOS 下唯一可用的鼠标模式**。
- 位移范围 -128 ~ +127，超出需拆成多帧。
- 单击动作：先发带按键位的帧，再发按键位清零的帧。

---

## 10. MOUSE_ABS（TYPE 0x12）

PAYLOAD 固定 6 字节。

| 偏移 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 0 | Buttons | uint8 | 同 9.1 |
| 1~2 | x | uint16 LE | 0 ~ 32767 |
| 3~4 | y | uint16 LE | 0 ~ 32767 |
| 5 | wheel | int8 | 同第 9 节 |

### 10.1 坐标系统

| 位置 | 坐标 |
|---|---|
| 左上角 | (0, 0) |
| 右下角 | (32767, 32767) |

### 10.2 约束

- **BIOS 不保证支持绝对坐标**，仅建议在 OS 下使用。
- 上位机负责提供模式切换，由用户决定当前使用相对还是绝对。
- 控制器不校验越界，上位机负责。

---

## 11. QUERY_KEYBOARD_STATE（0x14）/ REPORT_KEYBOARD_STATE（0x13）

### 11.1 语义

查询的是**目标机键盘的锁定指示状态**（Num / Caps / Scroll 等），
不是控制器自身的指示。控制器作为虚拟设备没有物理指示灯，
因此命名为 `KEYBOARD_STATE` 而非 `LED`。

### 11.2 请求

`QUERY_KEYBOARD_STATE`：PAYLOAD 长度 0。

**仅在 CONTROL 模式下有效**；PASSTHROUGH 下静默忽略，不回复。

### 11.3 响应

`REPORT_KEYBOARD_STATE`：PAYLOAD 固定 1 字节。

| Bit | 含义 |
|---|---|
| 0 | Num Lock |
| 1 | Caps Lock |
| 2 | Scroll Lock |
| 3 | Compose |
| 4 | Kana |
| 5~6 | 保留，填 0 |
| **7** | **valid**：`1`=已从目标机获取，`0`=尚未获取/未知 |

### 11.4 valid 位的必要性

状态来源是目标机 → 控制器的 **HID OUT report（SET_REPORT）**。
许多 BIOS **从不发送** SET_REPORT，此时控制器必须返回 `valid = 0`，
使上位机能够区分"灯全灭"与"状态未知"，避免误显示。

### 11.5 缓存规则

| 事件 | 缓存变化 |
|---|---|
| 收到 SET_REPORT | 更新缓存，`valid = 1`，**不发送任何帧** |
| 上电后未收到 SET_REPORT | 缓存全 0，`valid = 0` |
| 控制器复位 | 缓存清空，`valid = 0` |

### 11.6 轮询

固件**不做任何推送**。需要实时性时由上位机主动轮询，
建议间隔 **>= 200 ms**。

---

## 12. PING（0x20）/ PONG（0x21）

### 12.1 PING

PAYLOAD 固定 1 字节。

| 偏移 | 字段 | 说明 |
|---|---|---|
| 0 | tag | 0~255，上位机生成，用于匹配请求 |

### 12.2 PONG

PAYLOAD 固定 4 字节。

| 偏移 | 字段 | 说明 |
|---|---|---|
| 0 | tag | **原样回显** PING 的 tag |
| 1 | mode | `0` = PASSTHROUGH，`1` = CONTROL |
| 2 | version | 协议版本，当前 `0x01` |
| 3 | reserved | `0x00` |

### 12.3 用途

- 存活检查
- **模式确认**：`ENTER_CONTROL` 无响应，靠 PONG 的 `mode` 确认是否切换成功
- 协议版本校验
- 并发请求匹配（tag）

### 12.4 约束

**PING 只在 CONTROL 模式下有效。** PASSTHROUGH 下收到 PING 静默忽略。

上位机应先发 `ENTER_CONTROL`，再发 `PING`。建议超时 **100 ms**。

---

## 13. 流式解析

### 13.1 状态

| 状态 | 行为 |
|---|---|
| `SCAN` | 匹配 MAGIC；已确认非帧的字节按透传规则处理 |
| `HEADER` | 收 VERSION / TYPE / LENGTH |
| `PAYLOAD` | 收 N 字节 |
| `CHECK` | 收 4 字节 FNV 并校验 |

### 13.2 解析原则

1. UART 是字节流，帧头可能跨越多次读取，必须逐字节喂入状态机。
2. **每次失败判定至少将缓冲前移 1 字节**，保证解析器必定有进度，
   不存在死循环。
3. MAGIC 无前缀自重叠（见 5.4），因此失败时"已匹配的前缀字节"
   可整段前移，不会漏掉嵌套在伪帧里的真实帧起点。
4. 缓冲区上限 `MAX_FRAME`（1040 字节）。

### 13.3 判定流程

```c
/* 伪代码：buf 为待解析缓冲，buf_len 为有效长度 */
static void parse_loop(void)
{
    for (;;) {
        size_t avail = buf_len;

        /* 1) MAGIC 前缀匹配 */
        size_t k = common_prefix_len(buf, avail, MAGIC, 8);

        if (k < 8) {
            if (k == avail && avail < 8) {
                return;                    /* 全是前缀，等待更多字节 */
            }
            /* buf[k] 破坏了前缀，前 k 字节确定不是帧；
               若 k==0 说明 buf[0] 本身不是 MAGIC[0] */
            size_t n = (k > 0) ? k : 1;
            emit_non_frame(buf, n);        /* PASSTHROUGH 转发 / CONTROL 丢弃 */
            buf_shift(n);
            continue;
        }

        /* 2) MAGIC 完整，检查头部 */
        if (avail < 12) return;            /* 等待 VERSION/TYPE/LENGTH */

        uint8_t  ver  = buf[8];
        uint8_t  type = buf[9];
        uint16_t len  = (uint16_t)(buf[10] | (buf[11] << 8));

        if (ver != PROTO_VERSION || len > MAX_PAYLOAD) {
            emit_non_frame(buf, 1);        /* A 类失败 */
            buf_shift(1);
            continue;
        }

        /* 3) 等待完整帧 */
        if (avail < (size_t)(12 + len + 4)) return;

        /* 4) 校验 */
        uint32_t calc = fnv1a32(buf + 8, (size_t)(4 + len));
        uint32_t recv = read_le32(buf + 12 + len);

        if (calc != recv) {
            emit_non_frame(buf, 1);        /* A 类失败 */
            buf_shift(1);
            continue;
        }

        /* 5) 帧成立且校验通过 */
        dispatch_frame(type, buf + 12, len);
        buf_shift((size_t)(12 + len + 4));
    }
}

/* PASSTHROUGH 下写入 CDC；CONTROL 下直接丢弃 */
static void emit_non_frame(const uint8_t *p, size_t n)
{
    if (mode == MODE_PASSTHROUGH) {
        cdc_write(p, n);
    }
}
```

### 13.4 失败分类与处理（关键）

失败分两类，处理方式**不同**。

| 类别 | 判定条件 | 处理 | 理由 |
|---|---|---|---|
| **A 类：帧不成立** | MAGIC 前缀失配<br>VERSION 不认识<br>LENGTH > 1024<br>FNV 校验失败<br>帧内超时（见 13.5） | **回退转发**<br>（PASSTHROUGH 下原样写 CDC；CONTROL 下丢弃） | 这些字节可能本来就是透传数据，不能吞掉 |
| **B 类：帧成立但不处理** | MAGIC + VERSION + LENGTH + FNV 全部正确，但：<br>① TYPE 未知<br>② PASSTHROUGH 下收到非 `ENTER_CONTROL` 帧 | **整帧丢弃，不回退** | 这是控制端主动构造的完整帧，转发会污染目标机 |

### 13.5 超时

| 状态 | 超时 | 处理 |
|---|---|---|
| `HEADER` / `PAYLOAD` / `CHECK` | **100 ms** 无新字节 | 判定为 A 类失败：缓冲内字节全部 `emit_non_frame`，回 `SCAN` |
| `SCAN` | 无超时 | 持续工作 |

**超时值的约束**：115200 下最坏帧 1040 字节约需 90 ms，
因此超时不得小于 100 ms，否则会误杀正常的长帧。

**已知副作用**：若透传数据中恰好出现 MAGIC 前缀，这部分字节的转发
会延迟至多 100 ms。对交互式 putty 操作无感；对大流量二进制透传
可能出现一次瞬时卡顿，概率极低，可接受。

---

## 14. 上位机行为流程

### 14.1 连接/复位后同步

```text
1. 发送 ENTER_CONTROL
2. 等待 20 ms
3. 发送 PING(tag = 任意)
4. 期待 PONG
   ├─ 收到，且 mode == 1  → 同步完成
   └─ 100 ms 超时        → 重试；连续 3 次失败则报错退出
```

说明：上位机无需处理 bootloader 日志。解析器依靠 MAGIC 自动同步，
会跳过复位后 UART 上的非帧数据。

### 14.2 查询键盘状态

```text
发送 QUERY_KEYBOARD_STATE
期待 REPORT_KEYBOARD_STATE（建议超时 100 ms）
检查 PAYLOAD bit7（valid）
```

### 14.3 操作键鼠

仅在 CONTROL 模式下发 `KEYBOARD` / `MOUSE_REL` / `MOUSE_ABS`，均无响应。

### 14.4 退出

```text
1. 发送全释放键盘报告（8 字节全 0x00）
2. 发送鼠标按键清零报告
3. 发送 EXIT_CONTROL
4. 继续解析 UART RX 最多 100 ms，丢弃残余响应帧
5. 恢复透传使用
```

### 14.5 异常检测与重同步

| 现象 | 判定 | 处理 |
|---|---|---|
| PING 超时 | 控制器已复位，或不在 CONTROL | 重新执行 14.1 |
| QUERY 超时 | 同上 | 重新执行 14.1 |
| 收到 FNV 错误的帧 | 链路噪声 | 丢弃并计数；连续多次则重新执行 14.1 |
| 透传数据异常 | 可能误触发切模式 | 发 EXIT_CONTROL 后重新执行 14.1 |

**注意**：控制器一旦复位，模式回到 PASSTHROUGH。
上位机**必须重新 `ENTER_CONTROL`**，不能假设模式保持。

### 14.6 RESET 流程

`RESET` 没有响应帧，上位机不能靠"等应答"判断成败，必须按下面步骤判定：

```text
1. 确认已处于 CONTROL（否则先执行 14.1）
2. 发送 RESET（0x03，PAYLOAD 0）
3. 等待 >= 1 s（芯片重启 + USB 重新枚举 + mount）
4. 发送 PING(tag)
   ├─ 超时（无 PONG）   → 设备确实重启了（模式已回 PASSTHROUGH），继续第 5 步
   └─ 收到 PONG(mode=1) → 设备没有重启（固件不支持 0x03 或帧被丢弃）→ 失败
5. 重新执行 14.1，同步回 CONTROL
```

判据依据：复位后模式回到 PASSTHROUGH，而 PING 在 PASSTHROUGH 下静默
（§12.4）。因此"复位成功"与"固件忽略 RESET"在同一时刻表现完全相反：
前者 PING 超时，后者 PING 立即返回 `mode = 1`。

**注意**：复位会让目标机侧的 USB 设备消失再出现（§4.5），目标机上已打开的
CDC 串口句柄必然失效，需要重新打开——这是 USB 固有行为，与模式机无关。

---

## 15. 错误处理约定

### 15.1 A 类（帧不成立，回退转发）

| 情况 | 控制器行为 |
|---|---|
| MAGIC 前缀失配 | 已确认非帧的前缀字节转发 CDC，重新扫描 |
| VERSION 不认识 | 前移 1 字节，重新扫描 |
| LENGTH > MAX_PAYLOAD | 前移 1 字节，重新扫描 |
| FNV 校验失败 | 前移 1 字节，重新扫描 |
| 帧内超时（100 ms） | 缓冲全部转发 CDC，回 SCAN |

### 15.2 B 类（帧成立但不处理，整帧丢弃）

| 情况 | 控制器行为 |
|---|---|
| TYPE 未知 | 丢弃整帧，不回退 |
| PASSTHROUGH 下收到非 ENTER_CONTROL 帧 | 丢弃整帧，不回退 |
| CONTROL 下 PAYLOAD 长度与 TYPE 不符 | 丢弃整帧，不回退 |
| `RESET` 的 PAYLOAD 长度 ≠ 0 | 丢弃整帧，**绝不重启**（§4.5） |

### 15.3 其他

| 情况 | 控制器行为 |
|---|---|
| UART 溢出 | 丢弃多余字节 |
| 任何错误 | **不发送 NAK / ERROR 帧** |

---

## 16. 实现注意事项

### 16.1 日志策略

ESP-IDF 的 `ESP_LOGx` 默认输出到 UART0（GPIO43/44），即 COM5，
会与协议数据混流，导致：

- PASSTHROUGH 下污染 putty 显示
- CONTROL 下干扰上位机解析器

| 日志类型 | 何时输出 | 处理要求 |
|---|---|---|
| **运行时 `ESP_LOGx`** | 持续、周期性 | **正式构建必须关闭**<br>`esp_log_level_set("*", ESP_LOG_NONE)` |
| **bootloader 日志** | 仅复位后 < 1 s | **不处理**。上位机解析器靠 MAGIC 自动跳过，putty 看到属正常现象 |

### 16.2 其他实现约束

1. PASSTHROUGH 下 UART TX **禁止插入任何协议字节**，只转发 CDC 数据。
2. CONTROL 下 UART TX 只在响应请求时发送，其余时间静默。
3. 解析器需支持 UART 中断级逐字节调用；中断内不做重活，
   组装完成后通过队列交给 TinyUSB 任务发送 HID 报告。
4. CONTROL 下 CDC 必须**持续读取并丢弃**，防止目标机侧发送缓冲
   溢出导致 CDC 卡死。
5. 键盘 8 字节 PAYLOAD 原样传给 HID 接口，控制器不做任何翻译。
6. 上行/下行帧共用同一套编解码与 FNV 实现，避免两侧行为不一致。

---

## 17. 预留扩展

以下为未来版本预留，当前**不实现**：

| 项 | 预留用途 |
|---|---|
| VERSION 升级 | 不兼容变更时升版本号 |
| TYPE `0x22` | ERROR 帧（当前明确不实现） |
| TYPE `0x30+` | 宏录制、批量文本输入、配置查询 |
| PAYLOAD 子命令 | 同一 TYPE 下细分功能 |

---

## 18. 变更记录

| 版本 | 变更 |
|---|---|
| 1.0 | 初版。定义双模式、帧格式、键鼠报告、流式解析 |
| 1.1 | 引入下行帧；新增 PING/PONG 与键盘状态帧；规定下行帧仅在 CONTROL 模式发送 |
| 1.2 | 新增第 3 章"固件行为准则"，固件改为纯请求-响应模型；`QUERY_LED_STATE` 改为 `QUERY_KEYBOARD_STATE`；`KEYBOARD_LED_STATE` 改为 `KEYBOARD_STATE`；删除所有异步推送；删除 CONTROL 超时自动回退；补充上位机重同步流程 |
| **1.3** | 第 13.4 节重写：失败分为 A 类（帧不成立，回退转发）与 B 类（帧成立不处理，整帧丢弃），修正 1.2 中"失败字节不转发"导致透传丢数据的缺陷；补充正确的滑窗前移算法与防死循环约束；`KEYBOARD_STATE` 改为 `REPORT_KEYBOARD_STATE`；14.1 删除"丢弃初始 1 s 数据"；16.1 明确区分运行时日志与 bootloader 日志 |
| **1.4** | 新增 `RESET`（TYPE `0x03`，PAYLOAD 0，仅 CONTROL 有效，无任何下行响应）：上位机可主动重启控制器。补充 §4.5（语义 / 与 `EXIT_CONTROL` 的分工 / 触发条件 / 复位后状态）、§14.6（无应答情况下如何判定 RESET 生效）、§15.2 一行 B 类规则、§3.4 与 §6 的表格条目。协议 VERSION 仍为 `0x01`（新增 TYPE 属向后兼容：旧固件把 `0x03` 当未知 TYPE 丢弃，旧上位机不会发送它） |
