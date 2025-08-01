MAIN_DEFAULT_CONFIG_DATA = """
config_version: v3
connection:
  auto_connect: false
controller:
  baud_rate: 9600
  port: auto
  timeout: 0.5
  type: ch9329
mouse:
  cursor_offset_x: 4
  cursor_offset_y: 6
  relative_speed: 0.6
  report_frequency: 60
paste_board:
  interval: 1
shortcut_keys:
  Alt+F4:
  - alt_left
  - f4
  Ctrl+Alt+Del:
  - ctrl_left
  - alt_left
  - delete
  Ctrl+Shift+Esc:
  - ctrl_left
  - shift_left
  - esc
  Meta+D:
  - win_left
  - d
  Meta+L:
  - win_left
  - l
  Meta+R:
  - win_left
  - r
ui:
  fullscreen_tip: true
  quick_paste: true
  tips_fullscreen: true
  window_auto_maximized: false
  window_auto_to_center: true
video:
  device: Integrated Webcam
  format: NV12
  keep_aspect_ratio: true
  resolution_x: 1280
  resolution_y: 720
video_record:
  encoding_bitrate: 10000000
  encoding_mode: ConstantQualityEncoding
  frame_rate: 0
  quality: HighQuality
"""
MAIN_DEFAULT_CONFIG_DATA = MAIN_DEFAULT_CONFIG_DATA.strip()


if __name__ == "__main__":
    pass
