uv pip freeze | Out-File ./data/requirements.txt -Encoding utf8

$requirementsPath = "./data/requirements.txt"
$requirementsForLinuxPath = "./data/requirements_for_posix.txt"
$patterns = "^pywin32", "^pyWinhook", "^win32_setctime"

(Get-Content -Path $requirementsPath) | Where-Object {
    -not ($_ -match ($patterns -join "|"))
} | Set-Content -Path $requirementsForLinuxPath -Encoding utf8
