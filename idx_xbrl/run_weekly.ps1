# IDX XBRL weekly update — Task Scheduler에서 호출되는 진입점.
#
# 동작:
#   1) 가장 최근에 IDX에 제출된 회계연도 데이터를 시도 (today.year, today.year-1 순)
#   2) update_financials.py 실행 → company_financials_5y.json 갱신
#   3) git add/commit/push 자동
#
# 로그: logs/run_weekly_YYYYMMDD_HHMMSS.log

param(
    [int]$Year = 0,
    [string]$Period = "audit",
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$siteRoot = Split-Path -Parent $here
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path $here "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir "run_weekly_$timestamp.log"

function Write-Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Write-Log "=== IDX XBRL weekly update start ==="
Write-Log "site root: $siteRoot"
Write-Log "log: $logFile"

# 회계연도 자동 결정: 4월 이후면 작년, 그 전이면 재작년 (IDX 감사보고서는 보통 4월 제출)
if ($Year -eq 0) {
    $now = Get-Date
    if ($now.Month -ge 5) {
        $Year = $now.Year - 1
    } else {
        $Year = $now.Year - 2
    }
}
Write-Log "target year=$Year period=$Period"

# update_financials.py 실행
try {
    Push-Location $here
    Write-Log "running update_financials.py..."
    $pyOutput = & python -X utf8 update_financials.py --year $Year --period $Period 2>&1
    $pyExit = $LASTEXITCODE
    foreach ($line in $pyOutput) { Write-Log $line }
    if ($pyExit -ne 0) {
        Write-Log "ERROR: python exited with $pyExit"
        Pop-Location
        exit $pyExit
    }
} finally {
    Pop-Location
}

# git status에 변경이 있는지 확인
Push-Location $siteRoot
try {
    $changed = & git status --porcelain data/company_financials_5y.json idx_xbrl/cache idx_xbrl/logs 2>&1
    if (-not $changed) {
        Write-Log "no changes to commit"
        Pop-Location
        exit 0
    }
    Write-Log "changes detected:"
    foreach ($l in $changed) { Write-Log "  $l" }

    if ($NoPush) {
        Write-Log "--NoPush set; skipping git commit/push"
        Pop-Location
        exit 0
    }

    & git add data/company_financials_5y.json data/company_financials_5y.backup.xbrl.*.json 2>&1 | ForEach-Object { Write-Log $_ }
    & git add idx_xbrl/cache idx_xbrl/logs 2>&1 | ForEach-Object { Write-Log $_ }

    $commitMsg = "data: IDX XBRL 자동 갱신 FY$Year ($Period) — $timestamp"
    & git commit -m $commitMsg 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Write-Log "git commit failed (exit $LASTEXITCODE) — likely no staged changes"
        Pop-Location
        exit 0
    }
    & git push origin main 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR: git push failed (exit $LASTEXITCODE)"
        Pop-Location
        exit $LASTEXITCODE
    }
    Write-Log "pushed to origin/main"
} finally {
    Pop-Location
}

Write-Log "=== done ==="
