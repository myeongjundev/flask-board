# privilege_revoke_bot.py를 작업 스케줄러에서 실행하는 래퍼. (과잉권한 자동 회수)
#
# 봇은 허용목록 밖 관리자를 찾아 Graylog로 신고만 한다. 회수는
# Graylog 알림 → n8n → 게시판 /api/admin/revoke 가 맡는다.
# 실행 기록은 logs\privilege_bot.log에 쌓인다. 이 파일이 스케줄링 증적이다.

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$LogDir = Join-Path $RepoRoot 'logs'
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogFile = Join-Path $LogDir 'privilege_bot.log'

function Write-Log([string]$Text) {
    Add-Content -Path $LogFile -Value $Text -Encoding utf8
}

# 봇은 표준 라이브러리만 쓰지만, 게시판과 같은 가상환경 파이썬을 우선한다.
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $Python) {
    Write-Log ("[{0}] NO_PYTHON" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    exit 3
}

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

# stderr를 파이프로 합치면 PowerShell 5.1이 오류로 끝내 버린다. 파일로 받는다.
$OutFile = Join-Path $env:TEMP 'privilege_bot.out'
$ErrFile = Join-Path $env:TEMP 'privilege_bot.err'

# 경로에 공백(SKT aleph)이 있어 따옴표로 감싸 넘긴다.
$BotPath = '"{0}"' -f (Join-Path $RepoRoot 'privilege_revoke_bot.py')

$proc = Start-Process -FilePath $Python `
    -ArgumentList $BotPath `
    -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $OutFile -RedirectStandardError $ErrFile
$code = $proc.ExitCode

#   0 = 정상(위반 없음 또는 신고 완료) / 1 = 게시판 조회 실패 / 2 = 키 누락
$verdict = switch ($code) {
    0 { 'OK' }
    1 { 'BOARD_FAILED' }
    2 { 'CONFIG_MISSING' }
    default { "EXIT_$code" }
}

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Log "[$stamp] $verdict (exit=$code)"
foreach ($f in @($OutFile, $ErrFile)) {
    if (Test-Path $f) {
        Get-Content $f -Encoding utf8 |
            Where-Object { $_ -ne '' } |
            ForEach-Object { Write-Log "    $_" }
        Remove-Item $f -ErrorAction SilentlyContinue
    }
}

exit $code
