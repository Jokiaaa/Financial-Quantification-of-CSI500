$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'

$Python = 'C:\Users\30855\Desktop\RSRS\.venv-qlib\Scripts\python.exe'
$Script = Join-Path $PSScriptRoot 'daily_qlib_update.py'
$LogDir = Join-Path $PSScriptRoot 'daily_update_logs'

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ((Get-Date -Format 'yyyyMMdd_HHmmss') + '.log')

Write-Host '开始检查并更新 Qlib 数据。程序会先下载、暂存、校验和备份，再写入正式目录。'
& $Python $Script update 2>&1 | Tee-Object -FilePath $Log
$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0) {
    Write-Host "更新完成。日志：$Log" -ForegroundColor Green
} else {
    Write-Host "更新没有完成，正式数据不会使用未通过校验的批次。日志：$Log" -ForegroundColor Red
}

exit $ExitCode
