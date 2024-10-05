import datetime
import os
import sys
import traceback


def write_message(path: str, message: str):
    with open(path, "a+") as f:
        f.write(f"{message}\n")


if __name__ == "__main__":
    try:
        from main import main

        return_code = main()
        sys.exit(return_code)
    except Exception as error:
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        log_path = os.path.join(base_path, "error.log")
        write_message(log_path, f"Error occurred at: {datetime.datetime.now()}\n")
        write_message(log_path, f"Exception message: {error}\n")
        write_message(log_path, traceback.format_exc())
        sys.exit(1)
