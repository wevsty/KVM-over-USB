# pyside6-lupdate.exe .\main.py -recursive .\ui -ts .\translate\trans_zh_cn.ts -no-obsolete -verbose
$root_path = (Get-Location).Path + "\*";
$code_files = Get-ChildItem -Path $root_path -Recurse -Include "*.py", "*.ui";
pyside6-lupdate.exe $code_files -ts .\translate\trans_zh_cn.ts -no-obsolete -verbose


pyside6-linguist .\translate\trans_zh_cn.ts

pyside6-lrelease .\translate\trans_zh_cn.ts -qm .\translate\trans_zh_cn.qm
