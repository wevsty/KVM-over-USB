$requirements_raw = uv pip freeze
$requirements_base_path = "./data/requirements.txt"
$requirements_for_windows = "./data/requirements_for_windows.txt"
$requirements_for_posix = "./data/requirements_for_posix.txt"

function FilterItems {
    [CmdletBinding()]
    param (
        [string[]]$RawData,
        # 允许外部传入需要过滤的正则表达式数组，如果不传则使用默认值
        [string[]]$ExcludePatterns = @(
            "black"
        )
    )

    $filtered_requirements = $RawData | Where-Object {
        $line = $_
        $keep = $true

        foreach ($pattern in $ExcludePatterns) {
            # 使用 -match 进行正则匹配
            if ($line -match $pattern) {
                $keep = $false
                break
            }
        }
        $keep
    }

    # 返回过滤后的字符串数组
    return $filtered_requirements
}

$dev_exclude_patterns = @(
    "black",
    "mypy-extensions",
    "click",
    "packaging",
    "pathspec",
    "platformdirs",
    "pytokens",
    "isort",
    "flake8",
    "mccabe",
    "pycodestyle",
    "pyflakes",
    "flake8-bugbear",
    "attrs",
    "nuitka"
)

$posix_exclude_patterns = @(
    "pywin32",
    "pyWinhook",
    "win32-setctime",
    "colorama"
)

$requirements_raw | Out-File $requirements_base_path -Encoding utf8

$filtered_requirements = FilterItems -RawData $requirements_raw -ExcludePatterns $dev_exclude_patterns
$filtered_requirements | Out-File $requirements_for_windows -Encoding utf8

$posix_filtered_requirements = FilterItems -RawData $filtered_requirements -ExcludePatterns $posix_exclude_patterns
$posix_filtered_requirements | Out-File $requirements_for_posix -Encoding utf8
