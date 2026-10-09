# 入口模块：原 main.py 已按功能拆分为 ui/app_main_window 包。
# 这里仅做兼容转发，保持 `from main import main` 的入口可用。
from ui.app_main_window.bootstrap import main

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
