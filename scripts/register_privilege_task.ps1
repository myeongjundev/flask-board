# privilege_revoke_bot.py를 주기적으로 실행하는 작업 스케줄러 항목을 등록한다.
#
#     powershell -ExecutionPolicy Bypass -File scripts\register_privilege_task.ps1
#     powershell -ExecutionPolicy Bypass -File scripts\register_privilege_task.ps1 -IntervalMin 60
#
# 되돌리기:
#
#     powershell -ExecutionPolicy Bypass -File scripts\unregister_privilege_task.ps1
#
# 이 스크립트는 시스템 설정을 바꾼다. 무엇이 등록되는지 먼저 보여주고,
# 확인을 받은 뒤에만 등록한다.

param(
    [int]$IntervalMin = 5,
    # 확인 프롬프트를 건너뛴다. 자동화에서 부를 때만 쓴다.
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'

# 로그인 경보 작업과 같은 폴더에 둔다. 제출이 끝나면 함께 지운다.
$TaskFolder  = '\SKT-ALEPH-TEMP'
$TaskName    = 'TEMP-privilege-revoke-bot-DELETE-AFTER-SUBMIT'
$RepoRoot    = Split-Path -Parent $PSScriptRoot
$WrapperPath = Join-Path $PSScriptRoot 'run_privilege_bot.ps1'
$LogPath     = Join-Path $RepoRoot 'logs\privilege_bot.log'

if (-not (Test-Path $WrapperPath)) {
    throw "래퍼를 찾을 수 없습니다: $WrapperPath"
}

Write-Output '등록할 내용:'
Write-Output "  폴더       : $TaskFolder"
Write-Output "  작업 이름  : $TaskName"
Write-Output "  실행       : powershell -ExecutionPolicy Bypass -File $WrapperPath"
Write-Output "  주기       : $IntervalMin 분마다 (무기한)"
Write-Output "  로그       : $LogPath"
Write-Output ''

if (-not $Yes) {
    $answer = Read-Host '등록할까요? (y/N)'
    if ($answer -ne 'y') { Write-Output '취소했습니다. 등록하지 않았습니다.'; exit 0 }
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$WrapperPath`"" `
    -WorkingDirectory $RepoRoot

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMin)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

$description = @'
[임시 작업 - 제출이 끝나면 삭제하세요]

SKT ALEPH 과잉권한 자동 회수 봇 실습.
privilege_revoke_bot.py가 허용목록 밖 관리자를 Graylog로 신고하고,
Graylog 알림 → n8n → 게시판이 권한을 회수합니다.

삭제: 저장소의 scripts\unregister_privilege_task.ps1 을 실행하세요.
'@

Register-ScheduledTask -TaskPath $TaskFolder -TaskName $TaskName -Action $action `
    -Trigger $trigger -Settings $settings -Description $description -Force | Out-Null

Write-Output "등록했습니다: $TaskFolder\$TaskName"
Write-Output ''
Write-Output '지금 한 번 실행:'
Write-Output "  Start-ScheduledTask -TaskPath '$TaskFolder\' -TaskName '$TaskName'"
Write-Output '결과 확인:'
Write-Output "  Get-ScheduledTaskInfo -TaskPath '$TaskFolder\' -TaskName '$TaskName'"
Write-Output "  Get-Content '$LogPath' -Tail 20"
