param(
    [switch]$Apply,
    [switch]$RunTest,
    [string]$DiscordWebhookName = 'Spidey Bot',
    [string]$N8nContainer = 'n8n',
    [string]$TestHost = '127.0.0.1'
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $RepoRoot '.env'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$ContainerWorkDir = "/tmp/flask-board-relocation-$Stamp"
$BackupDir = Join-Path $RepoRoot "backups\n8n\$Stamp"

function Read-DotEnv([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw ".env not found: $Path"
    }
    $result = @{}
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match '^\s*([^#][^=]*)=(.*)$') {
            $result[$matches[1].Trim()] = $matches[2]
        }
    }
    return $result
}

function Require-Value($Map, [string]$Name) {
    $value = $Map[$Name]
    if ([string]::IsNullOrWhiteSpace($value) -or $value -match '^<.+>$') {
        throw ".env value is missing or still a template: $Name"
    }
    return $value
}

$config = Read-DotEnv $EnvFile
$student = Require-Value $config 'STUDENT_NAME'
$securityKey = Require-Value $config 'SECURITY_API_KEY'
$adminKey = $config['ADMIN_API_KEY']
if ([string]::IsNullOrWhiteSpace($adminKey)) { $adminKey = $securityKey }
$slackWebhookUrl = $config['SLACK_WEBHOOK_URL']
$telegramBotToken = $config['TELEGRAM_BOT_TOKEN']
$telegramChatId = $config['TELEGRAM_CHAT_ID']

Write-Output '=== flask-board relocation check ==='
Write-Output "Project   : $RepoRoot"
Write-Output "Student   : $student"
Write-Output "n8n       : $N8nContainer"
Write-Output "Discord   : $DiscordWebhookName"
Write-Output "Apply     : $Apply"
Write-Output ''

docker inspect $N8nContainer --format '{{.State.Status}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "n8n container not found: $N8nContainer" }

docker exec $N8nContainer rm -rf $ContainerWorkDir
docker exec $N8nContainer mkdir -p $ContainerWorkDir
docker exec $N8nContainer n8n export:workflow --all --separate --output=$ContainerWorkDir
if ($LASTEXITCODE -ne 0) { throw 'Failed to export n8n workflows.' }

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
docker cp "${N8nContainer}:${ContainerWorkDir}/." $BackupDir | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Failed to create the local n8n backup.' }
Write-Output "Backup    : $BackupDir"

docker cp (Join-Path $PSScriptRoot 'audit_n8n_workflows.js') "${N8nContainer}:/tmp/audit_n8n_workflows.js" | Out-Null
docker exec $N8nContainer node /tmp/audit_n8n_workflows.js $ContainerWorkDir
if (-not $Apply) {
    Write-Output ''
    Write-Output 'Audit complete. Run the following command to apply changes:'
    Write-Output '  powershell -ExecutionPolicy Bypass -File scripts\relocate_environment.ps1 -Apply -RunTest'
    exit 0
}

docker cp (Join-Path $PSScriptRoot 'find_n8n_discord_webhook.js') "${N8nContainer}:/tmp/find_n8n_discord_webhook.js" | Out-Null
docker cp (Join-Path $PSScriptRoot 'update_n8n_workflows.js') "${N8nContainer}:/tmp/update_n8n_workflows.js" | Out-Null
$discordUrl = docker exec $N8nContainer node /tmp/find_n8n_discord_webhook.js $ContainerWorkDir $DiscordWebhookName
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($discordUrl)) {
    throw "Discord Webhook not found: $DiscordWebhookName"
}

docker exec `
    -e "STUDENT_NAME=$student" `
    -e "SECURITY_API_KEY=$securityKey" `
    -e "ADMIN_API_KEY=$adminKey" `
    -e "DISCORD_WEBHOOK_URL=$discordUrl" `
    -e "SLACK_WEBHOOK_URL=$slackWebhookUrl" `
    -e "TELEGRAM_BOT_TOKEN=$telegramBotToken" `
    -e "TELEGRAM_CHAT_ID=$telegramChatId" `
    $N8nContainer node /tmp/update_n8n_workflows.js $ContainerWorkDir
if ($LASTEXITCODE -ne 0) { throw 'Failed to update n8n workflow configuration.' }

docker exec $N8nContainer n8n import:workflow --separate --input=$ContainerWorkDir
if ($LASTEXITCODE -ne 0) { throw 'Failed to import n8n workflows.' }

$workflowIds = Get-ChildItem -LiteralPath $BackupDir -Filter '*.json' | ForEach-Object {
    (Get-Content -Raw -LiteralPath $_.FullName -Encoding UTF8 | ConvertFrom-Json).id
}
foreach ($workflowId in $workflowIds) {
    docker exec $N8nContainer n8n publish:workflow --id=$workflowId
    if ($LASTEXITCODE -ne 0) { throw "Failed to publish workflow: $workflowId" }
}

docker restart $N8nContainer | Out-Null
$healthy = $false
foreach ($attempt in 1..30) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:5678/healthz' -TimeoutSec 2
        if ($response.StatusCode -eq 200) { $healthy = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
}
if (-not $healthy) { throw 'n8n health check failed after restart.' }
Write-Output 'n8n update and publish complete'

if ($RunTest) {
    $python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw "Virtualenv Python not found: $python" }
    $previousPythonUtf8 = $env:PYTHONUTF8
    $env:PYTHONUTF8 = '1'
    $loginAlertPassed = $false
    foreach ($attempt in 1..10) {
        & $python (Join-Path $RepoRoot 'alert_sender.py')
        if ($LASTEXITCODE -eq 0) { $loginAlertPassed = $true; break }
        Start-Sleep -Seconds 2
    }
    $env:PYTHONUTF8 = $previousPythonUtf8
    if (-not $loginAlertPassed) { throw 'Login alert E2E test failed.' }

    $payload = @{
        host = $TestHost
        open = @(5000, 5678, 9000, 12201, 3306)
        student = $student
    } | ConvertTo-Json -Compress
    $vulnerabilityScanPassed = $false
    foreach ($attempt in 1..10) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Method Post `
                -Uri 'http://localhost:5678/webhook/vuln-scan' `
                -ContentType 'application/json' -Body $payload -TimeoutSec 20
            if ($response.StatusCode -eq 200) { $vulnerabilityScanPassed = $true; break }
        } catch {}
        Start-Sleep -Seconds 2
    }
    if (-not $vulnerabilityScanPassed) { throw 'Vulnerability scan E2E test failed.' }
    Write-Output 'E2E requests complete: login alert + vulnerability scan'
}

Write-Output ''
Write-Output 'Relocation complete.'
