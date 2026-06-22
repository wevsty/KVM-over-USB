# python .\script\generate_file_list.py
# pyside6-lupdate.exe "@files.lst" -ts .\translate\main_zh_cn.ts -no-obsolete -verbose
pyside6-lupdate.exe -extensions py,ui . -ts .\translate\main_zh_cn.ts -no-obsolete -verbose
pyside6-lupdate.exe -extensions py,ui . -ts .\translate\main_zh_tw.ts -no-obsolete -verbose

Copy-Item ".\.venv\Lib\site-packages\PySide6\translations\qtbase_zh_CN.qm" -Destination ".\translations\qtbase_zh_cn.qm"
Copy-Item ".\.venv\Lib\site-packages\PySide6\translations\qtbase_zh_TW.qm" -Destination ".\translations\qtbase_zh_tw.qm"

# pyside6-linguist .\translate\main_zh_cn.ts

pyside6-lrelease .\translate\main_zh_cn.ts -qm .\translations\main_zh_cn.qm
pyside6-lrelease .\translate\main_zh_tw.ts -qm .\translations\main_zh_tw.qm