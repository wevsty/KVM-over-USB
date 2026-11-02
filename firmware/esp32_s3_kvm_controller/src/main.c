/*
 * 应用入口：USB 复合设备（HID 键盘/鼠标 + CDC ACM）初始化、
 * UART0 ↔ CDC 透传任务、协议帧分发表（模式机 + 键鼠 + PONG/状态回复）。
 *
 * SPDX-License-Identifier: MIT
 */

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include "esp_err.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

/* sdkconfig.h 必须先于 tinyusb_cdc_acm.h：后者直接 #error 检查 CONFIG_TINYUSB_CDC_ENABLED */
#include "sdkconfig.h"

#include "tinyusb.h"
#include "tinyusb_cdc_acm.h"
#include "tinyusb_default_config.h"

#include "usb_descriptors.h"
#include "kvm_proto.h"
#include "kvm_frame.h"
#include "kvm_parser.h"
#include "mode.h"
#include "hid.h"
#include "uart.h"
#include "app_log.h"

/* 枚举完成后的等待时间，留出目标机加载 HID 驱动的时间 */
#define APP_MOUNT_SETTLE_MS     (2000)
/* 等待枚举的轮询间隔 */
#define APP_MOUNT_POLL_MS       (100)
/* 空闲轮询周期（只为不让任务退出，不做任何主动输出） */
#define APP_IDLE_POLL_MS        (1000)

/* ===== UART0（GPIO43/44 / CH343 / COM5）↔ CDC 透传 =====
 *
 * PASSTHROUGH：UART RX → CDC TX（送目标机），CDC RX → UART TX（送回控制端）。
 * 约束：PASSTHROUGH 下 UART TX 不得出现协议字节（第 10 条）；
 *       CDC 回调只 give 信号量，收发都在独立任务里（第 18 条）。
 */

/* 单次从 CDC 读出的最大字节数（不要超过 CONFIG_TINYUSB_CDC_RX_BUFSIZE） */
#define APP_CDC_RX_BUF_SIZE         (256)
/* write_flush 超时（ticks）：0 = 不阻塞等待主机取数据 */
#define APP_CDC_FLUSH_TIMEOUT       (0)
/* RESET 前等待 UART TX 发完的最长时间（ms）：避免把上一帧的尾巴切断（§4.5） */
#define APP_RESET_TX_DRAIN_MS       (50)
/* 透传任务栈（字节）与优先级 */
#define APP_BRIDGE_TASK_STACK       (4096)
#define APP_BRIDGE_TASK_PRIO        (5)

static SemaphoreHandle_t s_cdc_rx_sem = NULL;

/**
 * @brief CDC 收到数据回调 —— 运行在 TinyUSB 任务上下文
 *
 * 只允许 give 信号量；禁止读写数据、禁止 write_flush、禁止任何阻塞/耗时操作。
 */
static void cdc_rx_callback(int itf, cdcacm_event_t *event)
{
    (void)itf;

    if (event->type != CDC_EVENT_RX || s_cdc_rx_sem == NULL) {
        return;
    }
    xSemaphoreGive(s_cdc_rx_sem);
}

/* ===== PASSTHROUGH / CONTROL 模式机 =====
 *
 * 模式状态在 mode.c，切换的唯一入口是下面分发表里的 ENTER_CONTROL / EXIT_CONTROL（§4）。
 * 解析器的两个出口在 app_main() 注入：
 *   A 类字节 → proto_emit_non_frame()（PASSTHROUGH 写 CDC / CONTROL 丢弃）；
 *   成立帧   → proto_dispatch_frame()（模式机 + HID 动作 + 下行响应）。
 */

/* USB/UART 数据通路是否已初始化完成：false 时一律不触碰 USB API（写 CDC 前会被丢弃） */
static bool s_bridge_ready = false;
/* 队列满告警只打一次：反复打印会把 COM5 变成日志流，污染协议通道 */
static bool s_warned_cdc_queue_full = false;

/**
 * @brief PASSTHROUGH 数据通路是否可用（§4.1）
 *
 * 两个条件同时满足才写 CDC：桥已初始化完成（之前不碰 USB API），且当前处于 PASSTHROUGH。
 * CONTROL 下 CDC 完全停止（§4.1），字节直接丢弃。
 */
static bool proto_passthrough_active(void)
{
    return s_bridge_ready && (mode_get() == MODE_PASSTHROUGH);
}

/**
 * @brief 把一段字节写进 CDC IN —— PASSTHROUGH 的 UART→CDC 方向
 *
 * 只在 PASSTHROUGH 且桥已就绪时写；CONTROL 下 CDC 完全停止（§4.1），字节直接丢弃。
 * 目标机未打开串口时同样丢弃，既不缓存也不阻塞：透传是即时语义，
 * 缓存旧数据只会让 putty 显示错位。
 */
static void cdc_write_bytes(const uint8_t *data, size_t len)
{
    if (!proto_passthrough_active() || (len == 0)) {
        return;
    }
    if (!tud_cdc_n_connected(TINYUSB_CDC_ACM_0)) {
        return;
    }

    const size_t queued = tinyusb_cdcacm_write_queue(TINYUSB_CDC_ACM_0, data, len);
    if ((queued < len) && !s_warned_cdc_queue_full) {
        s_warned_cdc_queue_full = true;
        APP_LOGW("cdc tx queue full: %u/%u bytes (target not reading)",
                 (unsigned)queued, (unsigned)len);
    }
    /* 超时 0：只把已有数据推给主机，不阻塞等待 */
    tinyusb_cdcacm_write_flush(TINYUSB_CDC_ACM_0, APP_CDC_FLUSH_TIMEOUT);
}

/**
 * @brief A 类处理：这些字节不构成帧，按透传规则处理（§13.4）
 *
 * PASSTHROUGH 下原样写 CDC；CONTROL 下丢弃（由 proto_passthrough_active() 决定，§4.1）。
 * 这是注入给 kvm_parser_init() 的 A 类出口。
 */
static void proto_emit_non_frame(const uint8_t *p, size_t n)
{
    cdc_write_bytes(p, n);
}

/**
 * @brief 该 TYPE 的固定 PAYLOAD 长度（§6）；未知 TYPE 返回 0xFFFF
 */
static uint16_t proto_type_payload_len(uint8_t type)
{
    switch (type) {
    case KVM_TYPE_ENTER_CONTROL:         return KVM_PAYLOAD_LEN_ENTER_CONTROL;
    case KVM_TYPE_EXIT_CONTROL:          return KVM_PAYLOAD_LEN_EXIT_CONTROL;
    case KVM_TYPE_RESET:                 return KVM_PAYLOAD_LEN_RESET;
    case KVM_TYPE_KEYBOARD:              return KVM_PAYLOAD_LEN_KEYBOARD;
    case KVM_TYPE_MOUSE_REL:             return KVM_PAYLOAD_LEN_MOUSE_REL;
    case KVM_TYPE_MOUSE_ABS:             return KVM_PAYLOAD_LEN_MOUSE_ABS;
    case KVM_TYPE_REPORT_KEYBOARD_STATE: return KVM_PAYLOAD_LEN_REPORT_KEYBOARD_STATE;
    case KVM_TYPE_QUERY_KEYBOARD_STATE:  return KVM_PAYLOAD_LEN_QUERY_KEYBOARD_STATE;
    case KVM_TYPE_PING:                  return KVM_PAYLOAD_LEN_PING;
    case KVM_TYPE_PONG:                  return KVM_PAYLOAD_LEN_PONG;
    default:                             return 0xFFFFu;
    }
}

/* ===== CONTROL 下的下行响应帧 =====
 *
 * 只允许 PONG 与 REPORT_KEYBOARD_STATE，且只在 CONTROL 下发送（第 10 / 11 条）。
 */

/**
 * @brief 发送一帧下行响应（只允许 PONG / REPORT_KEYBOARD_STATE）
 *
 * 非 CONTROL 一律拒发并告警 —— 这是第 10 条的运行期兜底：
 * PASSTHROUGH 的 UART TX 禁止出现任何协议字节。
 */
static void proto_send_downstream(uint8_t type, const uint8_t *payload, uint16_t len)
{
    if (!mode_is_control()) {
        APP_LOGW("downstream type=0x%02X refused: mode is not CONTROL", type);
        return;
    }
    if (len > KVM_PAYLOAD_LEN_PONG) {
        APP_LOGW("downstream type=0x%02X len=%u too large", type, (unsigned)len);
        return;
    }

    uint8_t frame[KVM_HEADER_LEN + KVM_PAYLOAD_LEN_PONG + KVM_CHECK_LEN];
    const size_t n = kvm_frame_encode(frame, sizeof(frame), type, payload, len);
    if (n == 0) {
        APP_LOGW("downstream type=0x%02X encode failed", type);
        return;
    }

    const int written = uart_bridge_write(frame, n);
    if (written != (int)n) {
        APP_LOGW("uart tx short write type=0x%02X: %d/%u", type, written, (unsigned)n);
    }
}

/**
 * @brief 帧成立且 FNV 通过后的分发：模式机（§4.3）+ 动作（§3.4）+ B 类判定（§15.2）
 *
 * 执行顺序固定：先做 PAYLOAD 长度校验（长度不符一律 B 类丢弃），再按 TYPE 处理。
 * 不产生任何响应的帧一律丢弃，绝不回退转发：帧是控制端主动构造的，转发会污染目标机。
 */
static void proto_dispatch_frame(uint8_t type, const uint8_t *payload, uint16_t len)
{
    const uint16_t expect = proto_type_payload_len(type);

    if (expect == 0xFFFFu) {
        APP_LOGW("frame type=0x%02X len=%u: unknown TYPE -> dropped (B class)",
                 type, (unsigned)len);
        return;
    }
    if (len != expect) {
        APP_LOGW("frame type=0x%02X len=%u: payload length mismatch (expect %u) "
                 "-> dropped (B class)",
                 type, (unsigned)len, (unsigned)expect);
        return;
    }

    switch (type) {
    case KVM_TYPE_ENTER_CONTROL:
        if (mode_is_control()) {
            /* §4.3：CONTROL 下 ENTER_CONTROL 幂等，保持 CONTROL，无副作用 */
            APP_LOGI("mode: ENTER_CONTROL in CONTROL -> already CONTROL (idempotent)");
        } else {
            mode_set(MODE_CONTROL);
            APP_LOGW("mode: PASSTHROUGH -> CONTROL (ENTER_CONTROL)");
        }
        break;

    case KVM_TYPE_EXIT_CONTROL:
        if (mode_get() == MODE_PASSTHROUGH) {
            /* §4.3：PASSTHROUGH 下 EXIT_CONTROL 属于"其他合法帧"→ B 类丢弃，无副作用 */
            APP_LOGW("frame type=0x02: EXIT_CONTROL in PASSTHROUGH -> dropped (B class)");
        } else {
            mode_set(MODE_PASSTHROUGH);
            APP_LOGW("mode: CONTROL -> PASSTHROUGH (EXIT_CONTROL)");
        }
        break;

    case KVM_TYPE_RESET:
        if (!mode_is_control()) {
            /* §4.3 / §15.2：PASSTHROUGH 下 RESET 属 B 类，整帧丢弃、绝不重启 */
            APP_LOGW("frame type=0x03: RESET in PASSTHROUGH -> dropped (B class)");
            break;
        }
        /* §4.5：仅 CONTROL 下生效。先等 UART TX 发完（<= 50 ms），把上一帧的尾巴
         * 送干净再重启；否则复位可能把正在发送的响应帧切断。 */
        APP_LOGW("RESET requested in CONTROL -> restarting controller (USB re-enumerate)");
        (void)uart_bridge_wait_tx_done(APP_RESET_TX_DRAIN_MS);
        esp_restart();
        break;  /* 不可达：esp_restart() 不返回；保留 break 避免 fallthrough 告警 */

    case KVM_TYPE_KEYBOARD: {
        if (!mode_is_control()) {
            /* §4.3 / §13.4 B 类：PASSTHROUGH 下非 ENTER_CONTROL 的合法帧整帧丢弃 */
            APP_LOGW("frame type=0x10: KEYBOARD in PASSTHROUGH -> dropped (B class)");
            break;
        }
        /* PAYLOAD 与 Boot 报告一一对应（§8）：modifier + reserved + 6 keycode。
         * 控制器不做键码翻译；reserved 由 tud_hid_n_keyboard_report() 固定写 0。 */
        uint8_t keycode[6];
        memcpy(keycode, &payload[2], sizeof(keycode));
        APP_HID_LOGI("hid kbd: mod=0x%02X keys=[%02X %02X %02X %02X %02X %02X]",
                     payload[0], keycode[0], keycode[1], keycode[2],
                     keycode[3], keycode[4], keycode[5]);
        hid_emit_keyboard(payload[0], keycode);
        break;
    }

    case KVM_TYPE_MOUSE_REL:
        if (!mode_is_control()) {
            APP_LOGW("frame type=0x11: MOUSE_REL in PASSTHROUGH -> dropped (B class)");
            break;
        }
        /* PAYLOAD 4 字节与 Report ID 1 的报告体完全相同（§9），原样送 HID */
        APP_HID_LOGI("hid mouse rel: btn=0x%02X dx=%d dy=%d wheel=%d",
                     payload[0], (int)(int8_t)payload[1], (int)(int8_t)payload[2],
                     (int)(int8_t)payload[3]);
        hid_emit_mouse(HID_MOUSE_REPORT_ID_RELATIVE, payload, KVM_PAYLOAD_LEN_MOUSE_REL);
        break;

    case KVM_TYPE_MOUSE_ABS:
        if (!mode_is_control()) {
            APP_LOGW("frame type=0x12: MOUSE_ABS in PASSTHROUGH -> dropped (B class)");
            break;
        }
        /* PAYLOAD 6 字节与 Report ID 2 的报告体完全相同（§10）；x/y 不校验越界（§10.2） */
        APP_HID_LOGI("hid mouse abs: btn=0x%02X x=%u y=%u wheel=%d",
                     payload[0], (unsigned)read_le16_bytes(&payload[1]),
                     (unsigned)read_le16_bytes(&payload[3]), (int)(int8_t)payload[5]);
        hid_emit_mouse(HID_MOUSE_REPORT_ID_ABSOLUTE, payload, KVM_PAYLOAD_LEN_MOUSE_ABS);
        break;

    case KVM_TYPE_PING: {
        if (!mode_is_control()) {
            /* §12.4：PASSTHROUGH 下 PING 静默忽略（不回复、不转发） */
            APP_LOGW("frame type=0x20: PING in PASSTHROUGH -> dropped (B class, §12.4)");
            break;
        }
        /* §12.2：tag 原样回显 + mode + version + reserved */
        const uint8_t pong[KVM_PAYLOAD_LEN_PONG] = {
            payload[0],
            (uint8_t)mode_get(),
            (uint8_t)KVM_VERSION,
            0x00,
        };
        proto_send_downstream((uint8_t)KVM_TYPE_PONG, pong, KVM_PAYLOAD_LEN_PONG);
        APP_LOGI("pong sent: tag=0x%02X mode=%u version=0x%02X",
                 payload[0], (unsigned)mode_get(), (unsigned)KVM_VERSION);
        break;
    }

    case KVM_TYPE_QUERY_KEYBOARD_STATE: {
        if (!mode_is_control()) {
            /* §11.2：PASSTHROUGH 下静默忽略，不回复 */
            APP_LOGW("frame type=0x14: QUERY in PASSTHROUGH -> dropped (B class, §11.2)");
            break;
        }
        const uint8_t state = hid_kbd_state();
        proto_send_downstream((uint8_t)KVM_TYPE_REPORT_KEYBOARD_STATE, &state,
                              KVM_PAYLOAD_LEN_REPORT_KEYBOARD_STATE);
        APP_LOGI("kbd state report sent: 0x%02X (valid=%u)", (unsigned)state,
                 (state & KVM_KBD_STATE_VALID) ? 1u : 0u);
        break;
    }

    case KVM_TYPE_REPORT_KEYBOARD_STATE:
    case KVM_TYPE_PONG:
        /* 下行专用 TYPE 出现在上行方向：无意义，B 类丢弃 */
        APP_LOGW("frame type=0x%02X: downstream-only TYPE received -> dropped (B class)",
                 type);
        break;

    default:
        /* 帧成立但没有对应动作：B 类整帧丢弃（绝不回退转发） */
        APP_LOGW("frame type=0x%02X len=%u: no action -> dropped (B class)",
                 type, (unsigned)len);
        break;
    }
}

/**
 * @brief CDC RX → UART TX 任务：把目标机侧（putty）输入送到控制端
 *
 * 回调只负责唤醒，读/写都在本任务里做；一次唤醒后把 CDC 里的数据读空。
 * CONTROL 下照样读空但**不写 UART**（CDC 完全停止，§4.1；持续读取是为了防止
 * 目标机侧发送缓冲溢出导致 CDC 卡死，§16.2 第 4 条）。
 * 只出现一次的告警用局部布尔量抑制：反复打印会把 COM5 变成日志流，污染协议通道。
 */
static void cdc_to_uart_task(void *arg)
{
    (void)arg;

    uint8_t buf[APP_CDC_RX_BUF_SIZE];
    bool warned_short_write = false;

    while (1) {
        if (xSemaphoreTake(s_cdc_rx_sem, portMAX_DELAY) != pdTRUE) {
            continue;
        }

        while (1) {
            size_t rx_size = 0;
            esp_err_t err = tinyusb_cdcacm_read(TINYUSB_CDC_ACM_0, buf, sizeof(buf), &rx_size);
            if (err != ESP_OK) {
                APP_LOGW("cdc read failed: %s", esp_err_to_name(err));
                break;
            }
            if (rx_size == 0) {
                break;
            }

            /* CONTROL 下 CDC 完全停止（§4.1）：数据必须读出来丢掉，
             * 不能停下不读，否则 CDC RX 缓冲堆满会让目标机侧收发卡死（§16.2 第 4 条）。 */
            if (mode_get() != MODE_PASSTHROUGH) {
                continue;
            }

            int written = uart_bridge_write(buf, rx_size);
            if ((written < 0) || ((size_t)written != rx_size)) {
                if (!warned_short_write) {
                    warned_short_write = true;
                    APP_LOGW("uart tx short write: %d/%u bytes", written, (unsigned)rx_size);
                }
            }
        }
    }
}

/**
 * @brief UART RX → CDC TX 任务：把控制端数据转发给目标机
 *
 * 目标机未打开串口（tud_cdc_n_connected() == false）时直接丢弃，
 * 既不缓存也不阻塞：透传是即时语义，缓存旧数据只会让 putty 显示错位。
 */
static void uart_to_cdc_task(void *arg)
{
    (void)arg;

    uint8_t buf[UART_BRIDGE_RX_CHUNK];

    while (1) {
        int len = uart_bridge_read(buf, sizeof(buf), UART_BRIDGE_READ_TIMEOUT_MS);
        if (len > 0) {
            /* 字节流全部交给解析器：
             *   A 类（非帧）字节 → 按当前模式处理（PASSTHROUGH 写 CDC，CONTROL 丢弃）；
             *   帧成立 → 交分发表（模式机 + KEYBOARD / MOUSE_REL / MOUSE_ABS / PING / QUERY 动作）。 */
            kvm_parser_feed(buf, (size_t)len);
        }

        /* 即使本轮没有新字节，也要检查帧内 100 ms 超时（§13.5）：
         * 半截帧卡在窗口里必须被冲刷出去，否则透传数据会被永久吞掉。 */
        kvm_parser_poll();
    }
}

/* ===== 应用入口 ===== */

void app_main(void)
{
    /* 协议 §16.1：COM5 与协议通道共用 UART0，发布态必须关闭运行时日志
     * （APP_LOGI 等只编译掉本工程调用点，挡不住 ESP-IDF 组件自己的日志）。
     * 现场排障时把 app_log.h 的 APP_PROTO_LOG 改为 1 重新烧录即可恢复。 */
#if !APP_PROTO_LOG
    esp_log_level_set("*", ESP_LOG_NONE);
#endif

    /* 解析器先注入两个出口，必须早于 uart2cdc 任务启动（任务里第一件事就是喂字节）：
     *   A 类字节 → proto_emit_non_frame()（PASSTHROUGH 写 CDC / CONTROL 丢弃）；
     *   成立帧   → proto_dispatch_frame()（模式机 + HID 动作 + 下行响应）。 */
    kvm_parser_init(proto_emit_non_frame, proto_dispatch_frame);

    ESP_LOGI(APP_LOG_TAG, "USB init: HID kbd (itf%d, boot) + HID mouse (itf%d, report) + CDC (itf%d/%d)",
             USB_HID_ITF_KEYBOARD, USB_HID_ITF_MOUSE, USB_CDC_ITF_COMM, USB_CDC_ITF_DATA);

    tinyusb_config_t tusb_cfg = TINYUSB_DEFAULT_CONFIG();

    /* device = NULL：使用 esp_tinyusb 内置 device descriptor（Espressif VID 0x303A） */
    tusb_cfg.descriptor.device = NULL;
    tusb_cfg.descriptor.full_speed_config = hid_configuration_descriptor;
    tusb_cfg.descriptor.string = hid_string_descriptor;
    tusb_cfg.descriptor.string_count = USB_STRING_DESC_COUNT;
#if (TUD_OPT_HIGH_SPEED)
    tusb_cfg.descriptor.high_speed_config = hid_configuration_descriptor;
#endif // TUD_OPT_HIGH_SPEED

    ESP_ERROR_CHECK(tinyusb_driver_install(&tusb_cfg));
    ESP_LOGI(APP_LOG_TAG, "USB init done, waiting for host mount");

    /* CDC 必须在 tinyusb_driver_install() 之后初始化：
     * 顺序颠倒会出现 COM 口但无数据通路。
     * 信号量先建好，避免 cdc_rx_callback 拿到 NULL 句柄。 */
    s_cdc_rx_sem = xSemaphoreCreateBinary();
    ESP_ERROR_CHECK(s_cdc_rx_sem != NULL ? ESP_OK : ESP_ERR_NO_MEM);

    static const tinyusb_config_cdcacm_t cdc_cfg = {
        .cdc_port = TINYUSB_CDC_ACM_0,
        .callback_rx = cdc_rx_callback,
    };
    ESP_ERROR_CHECK(tinyusb_cdcacm_init(&cdc_cfg));

    /* 数据通路就绪：能否写 CDC 由 proto_passthrough_active() 决定（模式 + 就绪双重判断）。
     * 置位前保持 false：TinyUSB 尚未初始化时任务不会触碰 USB API。 */
    s_bridge_ready = true;

    /* UART0 ↔ CDC 透传：CDC 已按第 17 条在 tinyusb_driver_install() 之后初始化，
     * 这里再安装 UART0 驱动并启动两个方向的转发任务。 */
    ESP_ERROR_CHECK(uart_bridge_init());
    ESP_ERROR_CHECK(xTaskCreate(cdc_to_uart_task, "cdc2uart", APP_BRIDGE_TASK_STACK, NULL,
                                APP_BRIDGE_TASK_PRIO, NULL) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
    ESP_ERROR_CHECK(xTaskCreate(uart_to_cdc_task, "uart2cdc", APP_BRIDGE_TASK_STACK, NULL,
                                APP_BRIDGE_TASK_PRIO, NULL) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
    APP_LOGI("UART0 <-> CDC passthrough ready (%d 8N1, no flow control), "
             "protocol parser armed (MAGIC scan, %u ms intra-frame timeout), mode=%s",
             UART_BRIDGE_BAUD_RATE, (unsigned)KVM_FRAME_TIMEOUT_MS,
             (mode_is_control() ? "CONTROL" : "PASSTHROUGH"));

    /* 等待目标机完成枚举 */
    while (!tud_mounted()) {
        vTaskDelay(pdMS_TO_TICKS(APP_MOUNT_POLL_MS));
    }
    ESP_LOGI(APP_LOG_TAG, "USB mounted, settle %d ms before idle", APP_MOUNT_SETTLE_MS);
    vTaskDelay(pdMS_TO_TICKS(APP_MOUNT_SETTLE_MS));

    /* 主任务到此不再做任何主动输出：透传、帧解析与模式机全部由 cdc_to_uart_task /
     * uart_to_cdc_task 负责（第 11 条：固件不主动推送任何数据）。 */
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(APP_IDLE_POLL_MS));
    }
}
