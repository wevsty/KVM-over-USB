import os


def create_file_list(target_dir, output_lst):
    # 存储所有有效的源码文件和界面描述文件
    valid_files = []
    absolute_target = os.path.abspath(target_dir)

    for root, _, files in os.walk(absolute_target):
        if any(
            ignored in root
            for ignored in [".venv", "venv", "__pycache__", ".git"]
        ):
            continue

        for file in files:
            if file.endswith(".py") and not file.startswith("ui_"):
                valid_files.append(
                    os.path.join(root, file).replace(os.path.sep, "/")
                )
            elif file.endswith(".ui"):
                valid_files.append(
                    os.path.join(root, file).replace(os.path.sep, "/")
                )

    # 写入清单
    with open(output_lst, "w", encoding="utf-8") as f:
        for path in valid_files:
            f.write(path + "\n")


if __name__ == "__main__":
    # 执行文件生成
    script_path = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.join(script_path, "..")
    pyproject_path = os.path.join(project_path, "files.lst")
    create_file_list(project_path, pyproject_path)
