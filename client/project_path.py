import os.path
import sys

ARGV_DIRECTORY_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
SOURCE_DIRECTORY_PATH = os.path.dirname(os.path.abspath(__file__))
BINARY_DIRECTORY_PATH = ARGV_DIRECTORY_PATH


def project_source_directory_path(*paths: str) -> str:
    return str(os.path.join(SOURCE_DIRECTORY_PATH, *paths))


def project_binary_directory_path(*paths: str) -> str:
    return str(os.path.join(BINARY_DIRECTORY_PATH, *paths))


if __name__ == '__main__':
    pass
