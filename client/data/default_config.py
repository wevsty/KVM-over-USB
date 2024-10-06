MAIN_DEFAULT_CONFIG_DATA = """
ui:
  quick_paste: true
  fullscreen_state_alert: false
video:
  auto_connect: false
  device: None
  format: None
  keep_aspect_ratio: true
  resolution_x: 1920
  resolution_y: 1080
audio:
  audio_device_in: auto
  audio_device_out: auto
  audio_support: false
video_record:
  encoding_bitrate: 10000000
  encoding_mode: ConstantQualityEncoding
  frame_rate: 0
  quality: HighQuality
controller:
  port: auto
  baud: 9600
mouse:
  mouse_report_freq: 60
  mouse_relative_speed: 0.6
paste_board:
  interval: 1
shortcut_keys:
  Ctrl+Alt+Del:
    - ctrl_left
    - alt_left
    - delete
  Ctrl+Shift+Esc:
    - ctrl_left
    - shift_left
    - esc
  Alt+F4:
    - alt_left
    - f4
  Meta+L:
    - win_left
    - l
  Meta+R:
    - win_left
    - r

"""


if __name__ == '__main__':
    pass
