# alert_sender.py를 5분마다 실행하는 작업 스케줄러 항목을 등록한다. (심화 S4)
#
# 사용법 (관리자 권한 필요 없음 - 현재 사용자 계정으로 등록된다):
#
#     powershell -ExecutionPolicy Bypass -File scripts\register_alert_task.ps1
#
# 되돌리기:
#
#     powershell -ExecutionPolicy Bypass -File scripts\unregister_alert_task.ps1
#
# 이 스크립트는 시스템 설정을 바꾼다. 무엇이 등록되는지 먼저 보여주고,
# 확인을 받은 뒤에만 등록한다.

param(
    # 확인 프롬프트를 건너뛴다. 자동화에서 부를 때만 쓴다.
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'

# 이름과 폴더를 일부러 눈에 띄게 둔다. 제출이 끝나면 지워야 하는 임시 작업이라,
# 작업 스케줄러 목록에서 한눈에 찾히고 무엇인지 바로 읽혀야 한다.
$TaskFolder  = '\SKT-ALEPH-TEMP'
$TaskName    = 'TEMP-alert-sender-5min-DELETE-AFTER-SUBMIT'
$RepoRoot    = Split-Path -Parent $PSScriptRoot
$WrapperPath = Join-Path $PSScriptRoot 'run_alert_sender.ps1'
$IntervalMin = 5

if (-not (Test-Path $WrapperPath)) {
    throw "래퍼를 찾을 수 없습니다: $WrapperPath"
}

# 스케줄러 세션에서도 같은 파이썬을 쓰도록 지금 경로를 확정해 둔다.
$PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonPath) { throw 'python을 PATH에서 찾지 못했습니다.' }

$LogPath = Join-Path $RepoRoot 'logs\alert_sender.log'

Write-Output '등록할 내용:'
Write-Output "  폴더       : $TaskFolder"
Write-Output "  작업 이름  : $TaskName"
Write-Output "  실행       : powershell -ExecutionPolicy Bypass -File $WrapperPath"
Write-Output "  주기       : $IntervalMin 분마다 (무기한)"
Write-Output "  파이썬     : $PythonPath"
Write-Output "  로그       : $LogPath"
Write-Output ''

if (-not $Yes) {
    $answer = Read-Host '등록할까요? (y/N)'
    if ($answer -ne 'y') { Write-Output '취소했습니다. 등록하지 않았습니다.'; exit 0 }
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WrapperPath`"" `
    -WorkingDirectory $RepoRoot

# 지금부터 시작해서 5분마다, 기간 제한 없이 반복한다.
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMin)

# 배터리로 돌아가는 노트북에서도 멈추지 않게. 창은 띄우지 않는다.
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

$description = @'
[임시 작업 - 제출이 끝나면 삭제하세요]

SKT ALEPH 미니실습(로그인 경보 자동화 봇) 심화 S4 항목.
alert_sender.py를 5분마다 실행해 n8n Webhook으로 합성 경보를 보냅니다.

삭제: 저장소의 scripts\unregister_alert_task.ps1 을 실행하세요.
'@

Register-ScheduledTask -TaskPath $TaskFolder -TaskName $TaskName -Action $action `
    -Trigger $trigger -Settings $settings -Description $description -Force | Out-Null

[Environment]::SetEnvironmentVariable('ALERT_SENDER_PYTHON', $PythonPath, 'User')

Write-Output ''
Write-Output "등록했습니다: $TaskFolder\$TaskName"
Write-Output ''
Write-Output '지금 한 번 실행해 확인하려면:'
Write-Output "  Start-ScheduledTask -TaskPath '$TaskFolder\' -TaskName '$TaskName'"
Write-Output '결과 확인:'
Write-Output "  Get-ScheduledTaskInfo -TaskPath '$TaskFolder\' -TaskName '$TaskName'"
Write-Output "  Get-Content '$LogPath' -Tail 20"
Write-Output ''
Write-Output '제출이 끝나면 삭제하세요:'
Write-Output '  powershell -ExecutionPolicy Bypass -File scripts\unregister_alert_task.ps1'
