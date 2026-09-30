import os


def is_debugging() -> bool:
    # 检查调试器常见的环境变量（不同版本可能略有差异）
    debugger_flags = [
        "DEBUGPY_RUNNING",
        "PYTEST_CURRENT_TEST",
        "PYDEVD_USE_FRAME_EVAL",
        "VSCODE_DEBUGGER",
    ]
    for flag in debugger_flags:
        if flag in os.environ:
            return True
    return False


debug_mode: bool = is_debugging()


if __name__ == "__main__":
    pass
