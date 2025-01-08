MAIN_DEFAULT_CONFIG_DATA = """
config_version: v2
audio:
  audio_device_in: None
  audio_device_out: None
  audio_support: false
controller:
  baud: 9600
  port: auto
mouse:
  cursor_offset_x: 4
  cursor_offset_y: 6
  relative_speed: 0.6
  report_freq: 60
paste_board:
  interval: 1
ui:
  fullscreen_tip: true
  quick_paste: true
video:
  auto_connect: false
  device: None
  format: None
  keep_aspect_ratio: true
  resolution_x: 1280
  resolution_y: 720
video_record:
  encoding_bitrate: 10000000
  encoding_mode: ConstantQualityEncoding
  frame_rate: 0
  quality: HighQuality
shortcut_keys:
  Alt+Tab:
  - alt_left
  - tab
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
  Meta+L:
  - win_left
  - l
  Meta+R:
  - win_left
  - r
"""
MAIN_DEFAULT_CONFIG_DATA = MAIN_DEFAULT_CONFIG_DATA.strip()


if __name__ == "__main__":
    pass
