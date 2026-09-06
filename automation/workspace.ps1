param(
    # 第一个位置参数是子命令，例如 validate、new-project 或 build-context。
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Command,

    # 其余参数不解释，原样转发给 Python CLI，避免 PowerShell 包装层重复维护契约。
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = 'Stop'

# 用脚本自身位置解析入口，因此可从工作区内任意目录调用本包装脚本。
# Python 选择集中在 python.ps1，可兼容公司环境、Windows Launcher 和 Codex 随附运行时。
$cliPath = Join-Path $PSScriptRoot 'scripts\workspace_cli.py'
$pythonRunner = Join-Path $PSScriptRoot 'python.ps1'
$forwardArgs = @($cliPath, $Command)
if ($RemainingArgs) {
    # PowerShell 会在“无剩余参数”时把可变参数绑定成含空字符串的数组；过滤空值，
    # 否则 argparse 会看到一个无法识别的额外参数。
    $forwardArgs += @($RemainingArgs | Where-Object { $_ -ne '' })
}
& $pythonRunner @forwardArgs
exit $LASTEXITCODE
