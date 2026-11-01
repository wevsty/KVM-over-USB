# 项目组件（目录 src/）：用到的组件必须显式写进 REQUIRES（改名后不再自动依赖全部组件）。
idf_component_register(
    SRCS "main.c" "uart.c" "kvm_frame.c" "kvm_parser.c" "mode.c" "hid.c" "usb_descriptors.c" "fnv1a32.c"
    INCLUDE_DIRS "."
    REQUIRES esp_driver_uart esp_timer tinyusb esp_tinyusb
    )
