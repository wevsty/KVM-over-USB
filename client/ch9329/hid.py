HID_KEY_GRAVE = b"\x35"
HID_KEY_1 = b"\x1e"
HID_KEY_2 = b"\x1f"
HID_KEY_3 = b"\x20"
HID_KEY_4 = b"\x21"
HID_KEY_5 = b"\x22"
HID_KEY_6 = b"\x23"
HID_KEY_7 = b"\x24"
HID_KEY_8 = b"\x25"
HID_KEY_9 = b"\x26"
HID_KEY_0 = b"\x27"
HID_KEY_MINUS = b"\x2d"
HID_KEY_EQUAL = b"\x2e"
HID_KEYCODE_14 = b"\x89"
HID_KEY_BACKSPACE = b"\x2a"
HID_KEY_TAB = b"\x2b"
HID_KEY_Q = b"\x14"
HID_KEY_W = b"\x1a"
HID_KEY_E = b"\x08"
HID_KEY_R = b"\x15"
HID_KEY_T = b"\x17"
HID_KEY_Y = b"\x1c"
HID_KEY_U = b"\x18"
HID_KEY_I = b"\x0c"
HID_KEY_O = b"\x12"
HID_KEY_P = b"\x13"
HID_KEY_BRACKET_LEFT = b"\x2f"
HID_KEY_BRACKET_RIGHT = b"\x30"
HID_KEYCODE_29 = b"\x31"  # backslash
HID_KEY_CAPS_LOCK = b"\x39"
HID_KEY_A = b"\x04"
HID_KEY_S = b"\x16"
HID_KEY_D = b"\x07"
HID_KEY_F = b"\x09"
HID_KEY_G = b"\x0a"
HID_KEY_H = b"\x0b"
HID_KEY_J = b"\x0d"
HID_KEY_K = b"\x0e"
HID_KEY_L = b"\x0f"
HID_KEY_SEMICOLON = b"\x33"
HID_KEY_APOSTROPHE = b"\x34"
HID_KEYCODE_42 = b"\x32"
HID_KEY_ENTER = b"\x28"
HID_KEY_SHIFT_L = b"\xe1"
HID_KEYCODE_45 = b"\x64"
HID_KEY_Z = b"\x1d"
HID_KEY_X = b"\x1b"
HID_KEY_C = b"\x06"
HID_KEY_V = b"\x19"
HID_KEY_B = b"\x05"
HID_KEY_N = b"\x11"
HID_KEY_M = b"\x10"
HID_KEY_COMMA = b"\x36"
HID_KEY_PERIOD = b"\x37"
HID_KEY_SLASH = b"\x38"
HID_KEYCODE_56 = b"\x87"  # Unknown
HID_KEY_SHIFT_R = b"\xe5"
HID_KEY_CTRL_L = b"\xe0"
#
HID_KEY_ALT_L = b"\xe2"
HID_KEY_SPACE = b"\x2c"
HID_KEY_ALT_R = b"\xe6"
#
HID_KEY_CTRL_R = b"\xe4"
#
#
#
#
#
#
#
#
#
#
HID_KEY_INSERT = b"\x49"
HID_KEY_DELETE = b"\x4c"
#
#
HID_KEY_ARROW_LEFT = b"\x50"
HID_KEY_HOME = b"\x4a"
HID_KEY_END = b"\x4d"
#
HID_KEY_ARROW_UP = b"\x52"
HID_KEY_ARROW_DOWN = b"\x51"
HID_KEY_PAGE_UP = b"\x4b"
HID_KEY_PAGE_DOWN = b"\x4e"
#
#
HID_KEY_ARROW_RIGHT = b"\x4f"
HID_KEY_NUM_LOCK = b"\x53"
HID_KEY_KEYPAD_7 = b"\x5f"
HID_KEY_KEYPAD_4 = b"\x5c"
HID_KEY_KEYPAD_1 = b"\x59"
#
HID_KEY_KEYPAD_DIVIDE = b"\x54"
HID_KEY_KEYPAD_8 = b"\x60"
HID_KEY_KEYPAD_5 = b"\x5d"
HID_KEY_KEYPAD_2 = b"\x5a"
HID_KEY_KEYPAD_0 = b"\x62"
HID_KEY_KEYPAD_MULTIPLY = b"\x55"
HID_KEY_KEYPAD_9 = b"\x61"
HID_KEY_KEYPAD_6 = b"\x5e"
HID_KEY_KEYPAD_3 = b"\x5b"
HID_KEY_KEYPAD_DECIMAL = b"\x63"
HID_KEY_KEYPAD_SUBTRACT = b"\x56"
HID_KEY_KEYPAD_ADD = b"\x57"
HID_KEYCODE_107 = b"\x85"  # Unknown
HID_KEY_KEYPAD_ENTER = b"\x58"
#
HID_KEY_ESCAPE = b"\x29"
#
HID_KEY_F1 = b"\x3a"
HID_KEY_F2 = b"\x3b"
HID_KEY_F3 = b"\x3c"
HID_KEY_F4 = b"\x3d"
HID_KEY_F5 = b"\x3e"
HID_KEY_F6 = b"\x3f"
HID_KEY_F7 = b"\x40"
HID_KEY_F8 = b"\x41"
HID_KEY_F9 = b"\x42"
HID_KEY_F10 = b"\x43"
HID_KEY_F11 = b"\x44"
HID_KEY_F12 = b"\x45"
HID_KEY_PRINT_SCREEN = b"\x46"
HID_KEY_SCROLL_LOCK = b"\x47"
HID_KEY_PAUSE = b"\x48"
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# Japanese
# Japanese
# Japanese
# KoreaKC-L
# KoreaKC-R
# ACPI
# ACPI
# ACPI
HID_KEY_WIN_L = b"\xe3"
HID_KEY_WIN_R = b"\xe7"
HID_WIN_APP = b"\x65"
HID_KEY_NONE = b"\x00"

# Refernce: Appendix 1 - "CH9329 Key Code Table"
# Line number denotes the serial number in the documentation

HID_MAPPING = {
    "": (HID_KEY_NONE, False),
    "a": (HID_KEY_A, False),
    "b": (HID_KEY_B, False),
    "c": (HID_KEY_C, False),
    "d": (HID_KEY_D, False),
    "e": (HID_KEY_E, False),
    "f": (HID_KEY_F, False),
    "g": (HID_KEY_G, False),
    "h": (HID_KEY_H, False),
    "i": (HID_KEY_I, False),
    "j": (HID_KEY_J, False),
    "k": (HID_KEY_K, False),
    "l": (HID_KEY_L, False),
    "m": (HID_KEY_M, False),
    "n": (HID_KEY_N, False),
    "o": (HID_KEY_O, False),
    "p": (HID_KEY_P, False),
    "q": (HID_KEY_Q, False),
    "r": (HID_KEY_R, False),
    "s": (HID_KEY_S, False),
    "t": (HID_KEY_T, False),
    "u": (HID_KEY_U, False),
    "v": (HID_KEY_V, False),
    "w": (HID_KEY_W, False),
    "x": (HID_KEY_X, False),
    "y": (HID_KEY_Y, False),
    "z": (HID_KEY_Z, False),
    "1": (HID_KEY_1, False),
    "2": (HID_KEY_2, False),
    "3": (HID_KEY_3, False),
    "4": (HID_KEY_4, False),
    "5": (HID_KEY_5, False),
    "6": (HID_KEY_6, False),
    "7": (HID_KEY_7, False),
    "8": (HID_KEY_8, False),
    "9": (HID_KEY_9, False),
    "0": (HID_KEY_0, False),
    "enter": (HID_KEY_ENTER, False),
    "esc": (HID_KEY_ESCAPE, False),
    "escape": (HID_KEY_ESCAPE, False),
    "backspace": (HID_KEY_BACKSPACE, False),
    "tab": (HID_KEY_TAB, False),
    "space": (HID_KEY_SPACE, False),
    "bracket_left": (HID_KEY_BRACKET_LEFT, False),
    "bracket_right": (HID_KEY_BRACKET_RIGHT, False),
    "backslash": (HID_KEYCODE_29, False),
    # "europe_1": (HID_KEY_EUROPE_1, False),
    "semicolon": (HID_KEY_SEMICOLON, False),
    "apostrophe": (HID_KEY_APOSTROPHE, False),
    "grave": (HID_KEY_GRAVE, False),
    "comma": (HID_KEY_COMMA, False),
    "period": (HID_KEY_PERIOD, False),
    "slash": (HID_KEY_SLASH, False),
    "caps_lock": (HID_KEY_CAPS_LOCK, False),
    "f1": (HID_KEY_F1, False),
    "f2": (HID_KEY_F2, False),
    "f3": (HID_KEY_F3, False),
    "f4": (HID_KEY_F4, False),
    "f5": (HID_KEY_F5, False),
    "f6": (HID_KEY_F6, False),
    "f7": (HID_KEY_F7, False),
    "f8": (HID_KEY_F8, False),
    "f9": (HID_KEY_F9, False),
    "f10": (HID_KEY_F10, False),
    "f11": (HID_KEY_F11, False),
    "f12": (HID_KEY_F12, False),
    "print_screen": (HID_KEY_PRINT_SCREEN, False),
    "scroll_lock": (HID_KEY_SCROLL_LOCK, False),
    "pause": (HID_KEY_PAUSE, False),
    "insert": (HID_KEY_INSERT, False),
    "home": (HID_KEY_HOME, False),
    "page_up": (HID_KEY_PAGE_UP, False),
    "delete": (HID_KEY_DELETE, False),
    "del": (HID_KEY_DELETE, False),
    "end": (HID_KEY_END, False),
    "page_down": (HID_KEY_PAGE_DOWN, False),
    "arrow_right": (HID_KEY_ARROW_RIGHT, False),
    "arrow_left": (HID_KEY_ARROW_LEFT, False),
    "arrow_down": (HID_KEY_ARROW_DOWN, False),
    "arrow_up": (HID_KEY_ARROW_UP, False),
    "right": (HID_KEY_ARROW_RIGHT, False),
    "left": (HID_KEY_ARROW_LEFT, False),
    "down": (HID_KEY_ARROW_DOWN, False),
    "up": (HID_KEY_ARROW_UP, False),
    "num_lock": (HID_KEY_NUM_LOCK, False),
    "keypad_divide": (HID_KEY_KEYPAD_DIVIDE, False),
    "keypad_multiply": (HID_KEY_KEYPAD_MULTIPLY, False),
    "keypad_subtract": (HID_KEY_KEYPAD_SUBTRACT, False),
    "keypad_add": (HID_KEY_KEYPAD_ADD, False),
    "keypad_enter": (HID_KEY_KEYPAD_ENTER, False),
    "keypad_1": (HID_KEY_KEYPAD_1, False),
    "keypad_2": (HID_KEY_KEYPAD_2, False),
    "keypad_3": (HID_KEY_KEYPAD_3, False),
    "keypad_4": (HID_KEY_KEYPAD_4, False),
    "keypad_5": (HID_KEY_KEYPAD_5, False),
    "keypad_6": (HID_KEY_KEYPAD_6, False),
    "keypad_7": (HID_KEY_KEYPAD_7, False),
    "keypad_8": (HID_KEY_KEYPAD_8, False),
    "keypad_9": (HID_KEY_KEYPAD_9, False),
    "keypad_0": (HID_KEY_KEYPAD_0, False),
    "keypad_decimal": (HID_KEY_KEYPAD_DECIMAL, False),
    # modifiers
    "ctrl": (HID_KEY_CTRL_L, False),
    "ctrl_left": (HID_KEY_CTRL_L, False),
    "ctrl_right": (HID_KEY_CTRL_R, False),
    "shift": (HID_KEY_SHIFT_L, False),
    "shift_left": (HID_KEY_SHIFT_L, False),
    "shift_right": (HID_KEY_SHIFT_R, False),
    "alt": (HID_KEY_ALT_L, False),
    "alt_left": (HID_KEY_ALT_L, False),
    "alt_right": (HID_KEY_ALT_R, False),
    "win": (HID_KEY_WIN_L, False),
    "win_left": (HID_KEY_WIN_L, False),
    "win_right": (HID_KEY_WIN_R, False),
    "win_app": (HID_WIN_APP, False),
    "gui": (HID_KEY_WIN_L, False),
    "gui_left": (HID_KEY_WIN_L, False),
    "gui_right": (HID_KEY_WIN_R, False),
    # white spaces
    " ": (HID_KEY_SPACE, False),
    "\t": (HID_KEY_TAB, False),
    "\n": (HID_KEY_ENTER, False),
    # symbols
    "-": (HID_KEY_MINUS, False),
    "=": (HID_KEY_EQUAL, False),
    "[": (HID_KEY_BRACKET_LEFT, False),
    "]": (HID_KEY_BRACKET_RIGHT, False),
    "\\": (HID_KEYCODE_29, False),
    ";": (HID_KEY_SEMICOLON, False),
    "'": (HID_KEY_APOSTROPHE, False),
    "`": (HID_KEY_GRAVE, False),
    ",": (HID_KEY_COMMA, False),
    ".": (HID_KEY_PERIOD, False),
    "/": (HID_KEY_SLASH, False),
    # symbols (shift)
    "^": (HID_KEY_6, True),
    "_": (HID_KEY_MINUS, True),
    "{": (HID_KEY_BRACKET_LEFT, True),
    "|": (HID_KEYCODE_29, True),
    "}": (HID_KEY_BRACKET_RIGHT, True),
    "~": (HID_KEY_GRAVE, True),
    "!": (HID_KEY_1, True),
    '"': (HID_KEY_APOSTROPHE, True),
    "#": (HID_KEY_3, True),
    "$": (HID_KEY_4, True),
    "%": (HID_KEY_5, True),
    "&": (HID_KEY_7, True),
    "(": (HID_KEY_9, True),
    ")": (HID_KEY_0, True),
    "*": (HID_KEY_8, True),
    "+": (HID_KEY_EQUAL, True),
    ":": (HID_KEY_SEMICOLON, True),
    "<": (HID_KEY_COMMA, True),
    ">": (HID_KEY_PERIOD, True),
    "?": (HID_KEY_SLASH, True),
    "@": (HID_KEY_2, True),
    # shift keys
    "A": (HID_KEY_A, True),
    "B": (HID_KEY_B, True),
    "C": (HID_KEY_C, True),
    "D": (HID_KEY_D, True),
    "E": (HID_KEY_E, True),
    "F": (HID_KEY_F, True),
    "G": (HID_KEY_G, True),
    "H": (HID_KEY_H, True),
    "I": (HID_KEY_I, True),
    "J": (HID_KEY_J, True),
    "K": (HID_KEY_K, True),
    "L": (HID_KEY_L, True),
    "M": (HID_KEY_M, True),
    "N": (HID_KEY_N, True),
    "O": (HID_KEY_O, True),
    "P": (HID_KEY_P, True),
    "Q": (HID_KEY_Q, True),
    "R": (HID_KEY_R, True),
    "S": (HID_KEY_S, True),
    "T": (HID_KEY_T, True),
    "U": (HID_KEY_U, True),
    "V": (HID_KEY_V, True),
    "W": (HID_KEY_W, True),
    "X": (HID_KEY_X, True),
    "Y": (HID_KEY_Y, True),
    "Z": (HID_KEY_Z, True),
}
