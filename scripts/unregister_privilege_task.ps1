# register_privilege_task.ps1로 등록한 임시 작업을 지운다.
#
#     powershell -ExecutionPolicy Bypass -File scripts\unregister_privilege_task.ps1
#
# 그대로 두면 주기마다 봇이 돌아 관리자 권한을 계속 회수한다.
# 로그 파일(logs\privilege_bot.log)은 증적이므로 지우지 않는다.

param(
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'

$TaskFolder = '\SKT-ALEPH-TEMP'
$TaskName   = 'TEMP-privilege-revoke-bot-DELETE-AFTER-SUBMIT'

$task = Get-ScheduledTask -TaskPath "$TaskFolder\" -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Output "등록된 작업이 없습니다: $TaskFolder\$TaskName"
    exit 0
}

if (-not $Yes) {
    $answer = Read-Host "$TaskFolder\$TaskName 을 지울까요? (y/N)"
    if ($answer -ne 'y') { Write-Output '취소했습니다.'; exit 0 }
}

Unregister-ScheduledTask -TaskPath "$TaskFolder\" -TaskName $TaskName -Confirm:$false
Write-Output "지웠습니다: $TaskFolder\$TaskName"
