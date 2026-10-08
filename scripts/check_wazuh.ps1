# Read-only checks for the Wazuh 4.9 classroom stack. Never prints passwords.
param([string]$AgentId = '')

$ErrorActionPreference = 'Stop'
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker CLI not found. Run this script on the PC hosting Wazuh Docker.'
}

Write-Output '[1] Wazuh containers'
docker ps -a --filter name=wazuh --format '{{.Names}} | {{.Status}} | {{.Ports}}'

Write-Output '[2] Agent connection'
docker exec wazuh-manager /var/ossec/bin/agent_control -l
if ($AgentId) {
    docker exec wazuh-manager /var/ossec/bin/agent_groups -s -i $AgentId
}

Write-Output '[3] Latest Manager alerts (metadata only)'
$wazuhAlertPython = @'
import json
import pathlib
p = pathlib.Path('/var/ossec/logs/alerts/alerts.json')
rows = []
if p.exists():
    with p.open('rb') as f:
        f.seek(max(0, p.stat().st_size - 200000))
        lines = f.read().decode('utf-8', errors='replace').splitlines()
    for line in lines:
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append({'time': r.get('timestamp'), 'agent': r.get('agent', {}).get('id'), 'rule': r.get('rule', {}).get('id')})
print(json.dumps(rows[-5:]))
'@
$wazuhAlertPython | docker exec -i wazuh-manager /var/ossec/framework/python/bin/python3 -

Write-Output '[4] Filebeat to Indexer'
docker exec wazuh-manager filebeat test output -c /etc/filebeat/filebeat.yml

Write-Output '[5] Actual Indexer alert count'
try {
    $wazuhEnvJson = docker inspect wazuh-manager --format '{{json .Config.Env}}' 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Manager unavailable' }
    $wazuhEnvItems = $wazuhEnvJson | ConvertFrom-Json
    $wazuhValues = @{}
    foreach ($wazuhItem in $wazuhEnvItems) {
        $wazuhPair = $wazuhItem -split '=', 2
        if ($wazuhPair.Count -eq 2) { $wazuhValues[$wazuhPair[0]] = $wazuhPair[1] }
    }
    if (-not $wazuhValues['INDEXER_USERNAME'] -or -not $wazuhValues['INDEXER_PASSWORD']) {
        throw 'Indexer credentials are not configured in Manager environment'
    }
    # Pass credentials through stdin, not command arguments or printed output.
    $wazuhAuth = ($wazuhValues['INDEXER_USERNAME'] + ':' + $wazuhValues['INDEXER_PASSWORD']).Replace('\', '\\').Replace('"', '\"')
    if ($wazuhAuth.Contains("`r") -or $wazuhAuth.Contains("`n")) { throw 'Unexpected credential format' }
    $wazuhQuery = if ($AgentId) { '?q=agent.id:' + [Uri]::EscapeDataString($AgentId) } else { '' }
    $wazuhCurlConfig = 'user = "' + $wazuhAuth + '"'
    $wazuhCurlConfig | docker exec -i wazuh-indexer curl --silent --show-error --max-time 15 --cacert /usr/share/wazuh-indexer/certs/root-ca.pem --config - ('https://wazuh.indexer:9200/wazuh-alerts-*/_count' + $wazuhQuery)
    if ($LASTEXITCODE -ne 0) { Write-Output 'Indexer query failed: inspect the error above.' }
} catch {
    Write-Output 'Indexer count unavailable. Check containers and configured credentials locally.'
}

Write-Output '[6] Actual Docker networks'
docker inspect wazuh-manager wazuh-indexer wazuh-dashboard --format '{{.Name}} {{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}'

Write-Output '[7] Recent Filebeat connection errors'
# Native stderr may contain log lines; avoid treating them as PowerShell exceptions.
$wazuhPreviousErrorMode = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
docker logs --since 5m wazuh-manager 2>&1 |
    Select-String -Pattern '401|Unauthorized|Failed to connect|DNS lookup failure' |
    Select-Object -Last 5
$ErrorActionPreference = $wazuhPreviousErrorMode

Write-Output 'Check Dashboard time range and selected Agent if Indexer count is positive.'
