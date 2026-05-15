$ErrorActionPreference = "Stop"
# 本脚本位于 scripts/，项目根为其上一级目录
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Error "未找到虚拟环境：$Py （请先创建 .venv 并安装依赖）"
}

& $Py (Join-Path $Root "scripts\png_to_ico.py")
& (Join-Path $Root ".venv\Scripts\pyinstaller.exe") --clean --noconfirm (Join-Path $Root "build_windows.spec")

Write-Host ""
Write-Host "打包完成：$(Join-Path $Root 'dist\文件传输助手.exe')"
