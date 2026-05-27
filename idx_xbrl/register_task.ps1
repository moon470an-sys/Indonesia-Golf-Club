# Windows Task Scheduler 등록 스크립트.
#
# 매주 일요일 02:00에 run_weekly.ps1을 실행하는 작업을 생성한다.
# 실행에는 PowerShell이 필요하며, 작업은 현재 사용자 권한으로 등록됨.
#
# Usage:
#   .\register_task.ps1                # 등록
#   .\register_task.ps1 -Unregister    # 제거
#   .\register_task.ps1 -RunNow        # 즉시 한 번 실행

param(
    [switch]$Unregister,
    [switch]$RunNow,
    [string]$TaskName = "MatoaGolfIDXXBRLWeekly",
    [string]$Time = "02:00"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $here "run_weekly.ps1"

if (-not (Test-Path $scriptPath)) {
    Write-Error "run_weekly.ps1 not found at $scriptPath"
    exit 1
}

if ($Unregister) {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Unregistered task: $TaskName"
    } else {
        Write-Host "Task $TaskName not found"
    }
    return
}

if ($RunNow) {
    Write-Host "Running run_weekly.ps1 once..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath
    return
}

# 기존 작업이 있으면 제거 후 재등록
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing task: $TaskName"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $Time

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

Register-ScheduledTask `
    -TaskName $TaskName `
    -Description "Matoa 골프장 IDX XBRL 주간 자동 갱신 — site/idx_xbrl/run_weekly.ps1" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal | Out-Null

Write-Host "Registered task: $TaskName"
Write-Host "  schedule: every Sunday at $Time"
Write-Host "  script:   $scriptPath"
Write-Host ""
Write-Host "View in Task Scheduler:  taskschd.msc"
Write-Host "Run manually:            .\register_task.ps1 -RunNow"
Write-Host "Remove:                  .\register_task.ps1 -Unregister"
