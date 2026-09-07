# This entry uses ASCII so Windows PowerShell 5.1 reads it consistently without a BOM.
# Downloads are public runtime files only; never send workspace content to a server.
$ErrorActionPreference = 'Stop'
$setupArgs = @($args)
$sourceRoot = Split-Path $PSScriptRoot -Parent
if ($setupArgs -contains '--help' -or $setupArgs -contains '-h') {
    Write-Output 'setup.cmd [--target OLD_WORKSPACE] [--profile core|full] [--offline] [--preview] [--register] [--open]'
    Write-Output 'setup.cmd --unregister | --rollback BACKUP_DIRECTORY'
    Write-Output 'Default: full install, preserve data/config, backup framework changes. core: no model downloads.'
    exit 0
}
# Prefer the destination runtime during upgrades: a GitHub ZIP has no Python of its own.
$targetIndex = [Array]::IndexOf($setupArgs, '--target')
if ($targetIndex -ge 0 -and $targetIndex + 1 -lt $setupArgs.Count) {
    $destinationPython = Join-Path $setupArgs[$targetIndex + 1] 'services\qdrant\runtime\python.exe'
    if (Test-Path -LiteralPath $destinationPython -PathType Leaf) { $env:CODEX_WORKSPACE_PYTHON = (Resolve-Path -LiteralPath $destinationPython).Path }
}
$runner = Join-Path $PSScriptRoot 'python.ps1'
$available = $false
try { & $runner -c 'import sys; print(sys.executable)'; $available = $LASTEXITCODE -eq 0 } catch { }
if (-not $available) {
    if ($setupArgs -contains '--preview' -or $setupArgs -contains '--offline') { throw 'Python 3.10+ missing; preview/offline will not download it. Use the old workspace runtime.' }
    if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { throw 'Only Windows x64 is supported.' }
    # Bootstrap stays local and is not registered with Windows or PATH.
    $bootstrap = Join-Path $sourceRoot '.local\bootstrap'
    New-Item -ItemType Directory -Force -Path $bootstrap | Out-Null
    $archive = Join-Path $bootstrap 'python.zip'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $bootstrap -Force
    Set-Content -LiteralPath (Join-Path $bootstrap 'python312._pth') -Encoding ASCII -Value "python312.zip`n.`nLib/site-packages`nimport site"
    # pip's standalone zipapp bootstraps the package downloader, without installing system pip.
    Invoke-WebRequest -UseBasicParsing 'https://bootstrap.pypa.io/pip/pip.pyz' -OutFile (Join-Path $bootstrap 'pip.pyz')
    $env:CODEX_WORKSPACE_PYTHON = Join-Path $bootstrap 'python.exe'
}
& $runner (Join-Path $PSScriptRoot 'scripts\deployment.py') @setupArgs
exit $LASTEXITCODE
