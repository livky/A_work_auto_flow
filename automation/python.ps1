# 不使用高级函数参数绑定：Python 的 -p/-v 不能被误识别为 PowerShell
# PythonArgs / Verbose 缩写，所有参数按原顺序转发。
$PythonArgs = @($args)

$ErrorActionPreference = 'Stop'

# 统一 PowerShell 与 Python 的标准流编码，避免中文路径和日志在 Windows 控制台乱码。
# 变量只影响当前包装脚本及其子进程，不修改用户或系统级环境。
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'

# 依次尝试显式覆盖、Windows Python Launcher、PATH 中的 python，以及 Codex 随附
# 运行时。候选项只保存可执行文件和前置参数，不修改 PATH 或用户环境。
$candidates = [System.Collections.Generic.List[object]]::new()

# 工作区便携运行时优先，不再依赖 Codex 缓存、全局 Python 或 Docker。
$workspacePython = Join-Path $PSScriptRoot '..\services\qdrant\runtime\python.exe'
if (Test-Path -LiteralPath $workspacePython -PathType Leaf) {
    $candidates.Add([pscustomobject]@{ File = $workspacePython; Prefix = @() })
}

if ($env:CODEX_WORKSPACE_PYTHON) {
    $candidates.Add([pscustomobject]@{ File = $env:CODEX_WORKSPACE_PYTHON; Prefix = @() })
}

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $candidates.Add([pscustomobject]@{ File = $pyLauncher.Source; Prefix = @('-3') })
}

$pathPython = Get-Command python -ErrorAction SilentlyContinue
if ($pathPython) {
    $candidates.Add([pscustomobject]@{ File = $pathPython.Source; Prefix = @() })
}

# Codex 桌面环境通常随附隔离 Python。路径从 USERPROFILE 派生而不是硬编码用户名，
# 并且只在文件实际存在时参与选择；普通公司终端没有此路径也不会受到影响。
if ($env:USERPROFILE) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython -PathType Leaf) {
        $candidates.Add([pscustomobject]@{ File = $bundledPython; Prefix = @() })
    }
}

$selected = $null
foreach ($candidate in $candidates) {
    try {
        # CLI 使用 Python 3.10+ 的类型语法。探测命令不导入工作区代码，也不写文件。
        $null = & $candidate.File @($candidate.Prefix) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>&1
        if ($LASTEXITCODE -eq 0) {
            $selected = $candidate
            break
        }
    }
    catch {
        # Windows Store 的 python.exe 等占位入口可能存在但无法启动；继续尝试下一项。
        continue
    }
}

if (-not $selected) {
    Write-Error '未找到可用的 Python 3.10+。请安装 Python，或把 CODEX_WORKSPACE_PYTHON 指向获批解释器。'
    exit 2
}

& $selected.File @($selected.Prefix) @PythonArgs
exit $LASTEXITCODE
