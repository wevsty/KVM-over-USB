# The following five lines of boilerplate have to be in your project's
# CMakeLists in this exact order for cmake to work correctly
cmake_minimum_required(VERSION 3.22)

# 项目组件目录用 src/（不是 ESP-IDF 默认的 main/），依据官方文档
# "Renaming main"：改名后必须在这里登记组件目录，并在 src/CMakeLists.txt
# 里自行声明依赖（main 组件「自动依赖所有组件」的特性随之失效）。
set(EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/src")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(kvm_controller)
