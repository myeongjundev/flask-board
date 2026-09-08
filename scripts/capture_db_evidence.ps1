# n8n이 게시판에 저장한 행을 보여준다. (증적 07)
#
#     powershell -ExecutionPolicy Bypass -File scripts\capture_db_evidence.ps1
#
# mysql -p<비밀번호>를 명령줄에 그대로 치면 그 비밀번호가 화면에 남는다.
# 제출용 캡처에 DB 비밀번호가 찍히면 E1 위반이다. 그래서 .env에서 읽어
# 컨테이너 안의 MYSQL_PWD로만 넘긴다. 화면에는 나오지 않는다.

$ErrorActionPreference = 'Stop'

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$Container  = 'flask_mysql'
$Database   = 'my_new_board_db'

$EnvPath = Join-Path $RepoRoot '.env'
if (-not (Test-Path $EnvPath)) { throw ".env를 찾을 수 없습니다: $EnvPath" }

$conf = @{}
foreach ($line in Get-Content $EnvPath -Encoding UTF8) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
        $conf[$Matches[1]] = $Matches[2].Trim().Trim('"')
    }
}
$Password = $conf['MYSQL_ROOT_PASSWORD']
if (-not $Password) { throw '.env에 MYSQL_ROOT_PASSWORD가 없습니다.' }

function Show-Query {
    param([string]$Title, [string]$Sql)

    Write-Host ''
    Write-Host $Title -ForegroundColor Cyan
    Write-Host ("-" * 78) -ForegroundColor DarkGray

    # -e로 비밀번호를 컨테이너 환경변수에만 전달한다. docker 명령줄에는 남지 않는다.
    $out = docker exec -e "MYSQL_PWD=$Password" $Container `
        mysql -uroot --table -e $Sql $Database
    if ($LASTEXITCODE -ne 0) { throw "쿼리 실패 (exit=$LASTEXITCODE)" }
    $out | ForEach-Object { Write-Host $_ }
}

Write-Host ''
Write-Host 'n8n이 게시판에 저장한 보안 이벤트' -ForegroundColor White
Write-Host '(DB 비밀번호는 .env에서 읽어 컨테이너 환경변수로만 넘깁니다)' -ForegroundColor DarkGray

Show-Query -Title '판정별 건수 — 거부와 허용이 모두 저장되었는가 (D6)' -Sql @'
SELECT source, decision, COUNT(*) AS rows_saved
FROM security_events
GROUP BY source, decision
ORDER BY source, decision;
'@

Show-Query -Title 'n8n이 최근 저장한 6건 — 학생 이름·출발지·판정 (D4)' -Sql @'
SELECT id, student, src_ip, decision, severity, fail_count
FROM security_events
WHERE source = 'login_alert_lab'
ORDER BY id DESC
LIMIT 6;
'@

Write-Host ''
