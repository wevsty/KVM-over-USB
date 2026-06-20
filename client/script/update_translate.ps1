# python .\script\generate_file_list.py
# pyside6-lupdate.exe "@files.lst" -ts .\translate\trans_zh_cn.ts -no-obsolete -verbose
pyside6-lupdate.exe -extensions py,ui . -ts .\translate\trans_zh_cn.ts -no-obsolete -verbose
pyside6-linguist .\translate\trans_zh_cn.ts
pyside6-lrelease .\translate\trans_zh_cn.ts -qm .\translate\trans_zh_cn.qm
