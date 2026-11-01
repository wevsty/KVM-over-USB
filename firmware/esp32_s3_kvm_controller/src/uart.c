/*
 * UART0（GPIO43/44 → CH343 → COM5）底层实现：初始化、读写、TX 排空。
 * 端口固定 UART_NUM_0，与控制台共用；引脚保持芯片默认，禁止改作他用。
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */

#include "uart.h"

#include "driver/uart.h"
#include "freertos/FreeRTOS.h"

/* 端口号固定：协议通道与控制台共用 UART0，禁止改作他用 */
#define UART_BRIDGE_PORT            UART_NUM_0

/* 驱动缓冲区（字节）：RX 留大一点，避免任务调度延迟时丢字节 */
#define UART_BRIDGE_RX_BUF_SIZE     (2048)
#define UART_BRIDGE_TX_BUF_SIZE     (1024)

esp_err_t uart_bridge_init(void)
{
    const uart_config_t cfg = {
        .baud_rate = UART_BRIDGE_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    esp_err_t err = uart_param_config(UART_BRIDGE_PORT, &cfg);
    if (err != ESP_OK) {
        return err;
    }

    /* 四个 UART_PIN_NO_CHANGE：沿用 GPIO43/44 */
    err = uart_set_pin(UART_BRIDGE_PORT, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE,
                       UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (err != ESP_OK) {
        return err;
    }

    /* 不使用事件队列：透传只需要读字节 */
    return uart_driver_install(UART_BRIDGE_PORT, UART_BRIDGE_RX_BUF_SIZE,
                               UART_BRIDGE_TX_BUF_SIZE, 0, NULL, 0);
}

int uart_bridge_write(const uint8_t *data, size_t len)
{
    if ((data == NULL) || (len == 0)) {
        return 0;
    }
    return uart_write_bytes(UART_BRIDGE_PORT, (const char *)data, len);
}

int uart_bridge_read(uint8_t *data, size_t len, int timeout_ms)
{
    if ((data == NULL) || (len == 0)) {
        return 0;
    }
    return uart_read_bytes(UART_BRIDGE_PORT, data, len, pdMS_TO_TICKS(timeout_ms));
}

bool uart_bridge_wait_tx_done(int timeout_ms)
{
    return uart_wait_tx_done(UART_BRIDGE_PORT, pdMS_TO_TICKS(timeout_ms)) == ESP_OK;
}