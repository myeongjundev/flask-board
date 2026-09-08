# 심화 S4로 등록한 임시 작업을 지운다.
#
#     powershell -ExecutionPolicy Bypass -File scripts\unregister_alert_task.ps1
#
# 제출이 끝나면 실행하세요. 그대로 두면 5분마다 계속 n8n으로 요청이 갑니다.
# 로그 파일(logs\alert_sender.log)은 증적이므로 지우지 않습니다.

param(
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'

$TaskFolder = '\SKT-ALEPH-TEMP'
$TaskName   = 'TEMP-alert-sender-5min-DELETE-AFTER-SUBMIT'

$task = Get-ScheduledTask -TaskPath "$TaskFolder\" -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    # 이전 이름으로 등록된 것이 남아 있을 수 있다.
    $legacy = Get-ScheduledTask -TaskName 'LoginAlertSender' -ErrorAction SilentlyContinue
    if ($legacy) {
        Write-Output '이전 이름(LoginAlertSender)으로 등록된 작업을 찾았습니다.'
        if (-not $Yes) {
            $answer = Read-Host '지울까요? (y/N)'
            if ($answer -ne 'y') { Write-Output '취소했습니다.'; exit 0 }
        }
        Unregister-ScheduledTask -TaskName 'LoginAlertSender' -Confirm:$false
        Write-Output '지웠습니다: LoginAlertSender'
        exit 0
    }
    Write-Output "등록된 작업이 없습니다: $TaskFolder\$TaskName"
    exit 0
}

Write-Output "지울 작업: $TaskFolder\$TaskName"
Write-Output "  상태: $($task.State)"

if (-not $Yes) {
    $answer = Read-Host '지울까요? (y/N)'
    if ($answer -ne 'y') { Write-Output '취소했습니다.'; exit 0 }
}

Unregister-ScheduledTask -TaskPath "$TaskFolder\" -TaskName $TaskName -Confirm:$false
Write-Output "지웠습니다: $TaskName"

# 폴더가 비었으면 폴더도 정리한다. 작업 스케줄러 목록에 빈 칸이 남지 않게.
try {
    $svc = New-Object -ComObject 'Schedule.Service'
    $svc.Connect()
    $root = $svc.GetFolder('\')
    $folder = $root.GetFolder($TaskFolder)
    if ($folder.GetTasks(1).Count -eq 0) {
        $root.DeleteFolder($TaskFolder.TrimStart('\'), 0)
        Write-Output "빈 폴더도 지웠습니다: $TaskFolder"
    }
} catch {
    Write-Output "폴더 정리는 건너뜁니다: $($_.Exception.Message)"
}

[Environment]::SetEnvironmentVariable('ALERT_SENDER_PYTHON', $null, 'User')
Write-Output '사용자 환경변수 ALERT_SENDER_PYTHON도 제거했습니다.'
Write-Output '로그(logs\alert_sender.log)는 증적이므로 남겨 두었습니다.'
