# alert_sender.py를 작업 스케줄러에서 안전하게 실행하는 래퍼. (심화 S4)
#
# 스케줄러는 시작 위치를 보장하지 않는다. 그대로 실행하면 alert_sender.py가
# 옆에 있는 .env를 못 찾아 "N8N_WEBHOOK_URL과 STUDENT_NAME을 .env에 설정하세요"로
# 끝난다. 그래서 이 래퍼가 저장소 폴더로 먼저 이동한다.
#
# 실행 기록은 logs\alert_sender.log에 쌓인다. 이 파일이 S4의 증적이다.

$ErrorActionPreference = 'Stop'

# 이 스크립트는 <저장소>\scripts\ 에 있으므로 부모가 저장소 폴더다.
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$LogDir = Join-Path $RepoRoot 'logs'
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogFile = Join-Path $LogDir 'alert_sender.log'

function Write-Log([string]$Text) {
    Add-Content -Path $LogFile -Value $Text -Encoding utf8
}

# 스케줄러 세션에는 PATH가 로그인 셸과 다르다. 파이썬 경로를 명시적으로 찾는다.
$Python = $env:ALERT_SENDER_PYTHON
if (-not $Python -or -not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $Python) {
    Write-Log ("[{0}] NO_PYTHON — ALERT_SENDER_PYTHON에 전체 경로를 넣으세요." -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    exit 3
}

$env:PYTHONUTF8 = '1'          # 한글 출력이 cp949에서 깨지지 않게
$env:PYTHONIOENCODING = 'utf-8'

# 파이썬을 직접 호출하고 stderr를 파이프로 합치면, Windows PowerShell 5.1은
# 그 한 줄 한 줄을 오류 레코드로 감싸고 $ErrorActionPreference='Stop' 때문에
# 스크립트가 그 자리에서 끝난다. 그러면 아래 로그가 절대 남지 않는다.
# 그래서 별도 프로세스로 띄우고 두 스트림을 파일로 받는다.
$OutFile = Join-Path $env:TEMP 'alert_sender.out'
$ErrFile = Join-Path $env:TEMP 'alert_sender.err'

$proc = Start-Process -FilePath $Python `
    -ArgumentList (Join-Path $RepoRoot 'alert_sender.py') `
    -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $OutFile -RedirectStandardError $ErrFile
$code = $proc.ExitCode

# 종료코드는 alert_sender.py가 정한 값 그대로다.
#   0 = 전송 성공 / 1 = 전송 실패(n8n 꺼짐·404 등) / 2 = .env 설정 누락
$verdict = switch ($code) {
    0 { 'OK' }
    1 { 'SEND_FAILED' }
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

# 스케줄러의 '마지막 실행 결과'에 그대로 나타난다.
exit $code
