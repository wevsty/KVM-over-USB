# 重新生成UI代码
# pyside6-uic main.ui -o main_u./i.py

$ui_path = (Get-Location).Path + "\*";
$ui_files = Get-ChildItem -Path $ui_path -Include "*.ui";

foreach ($ui_file in $ui_files){
    Write-Host "generate ui file: $ui_file";
    $ui_code_path = $ui_file.FullName.Replace(".", "_") + ".py";
    pyside6-uic $ui_file -o $ui_code_path
}
