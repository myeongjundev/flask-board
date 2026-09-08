# 게시판 보안 API의 응답 코드를 한 화면에 보여준다. (증적 11 · 12)
#
#     powershell -ExecutionPolicy Bypass -File scripts\capture_api_evidence.ps1
#
# 네 번을 순서대로 호출하고 기대값과 실제값을 나란히 찍는다.
#   401  키 없이 호출        (D1)
#   400  decision 빠뜨림     (D2)
#   201  정상 저장           (D3)
#   200  학생 이름으로 조회  (D5)
#
# API 키는 .env에서 읽되 화면에는 찍지 않는다. 캡처에 비밀값이 남으면 E1 위반이다.

$ErrorActionPreference = 'Stop'

# 콘솔 출력 인코딩은 건드리지 않는다. Windows PowerShell 5.1의 레거시 콘솔에서
# OutputEncoding만 UTF-8로 바꾸면 글자 폭 계산이 어긋나 한글이 두 번 그려진다.
# 이 스크립트의 한글은 전부 cp949에 있으므로 기본값 그대로가 맞다.

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BaseUrl  = 'http://127.0.0.1:5000'

# --- .env에서 키를 읽는다 (출력하지 않는다) ---------------------------------
$EnvPath = Join-Path $RepoRoot '.env'
if (-not (Test-Path $EnvPath)) { throw ".env를 찾을 수 없습니다: $EnvPath" }

$conf = @{}
foreach ($line in Get-Content $EnvPath -Encoding UTF8) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
        $conf[$Matches[1]] = $Matches[2].Trim().Trim('"')
    }
}
$ApiKey  = $conf['SECURITY_API_KEY']
$Student = $conf['STUDENT_NAME']
if (-not $ApiKey)  { throw '.env에 SECURITY_API_KEY가 없습니다.' }
if (-not $Student) { throw '.env에 STUDENT_NAME이 없습니다.' }

# 실제 사람의 주소를 쓰지 않는다. 203.0.113.0/24는 문서용 예약 대역이다.
$DemoIp = '203.0.113.7'

# --- 호출 한 번을 실행하고 결과를 한 덩어리로 찍는다 ------------------------
function Invoke-Case {
    param(
        [string]$Label,      # 화면에 보일 제목
        [string]$Grade,      # 배점 항목
        [int]$Expect,        # 기대 상태 코드
        [string]$Method,
        [string]$Path,
        [hashtable]$Headers = @{},
        $Body = $null        # 있으면 JSON으로 보낸다
    )

    $args = @{
        Uri             = "$BaseUrl$Path"
        Method          = $Method
        Headers         = $Headers
        UseBasicParsing = $true
    }
    if ($null -ne $Body) {
        # 한글이 섞여도 깨지지 않게 UTF-8 바이트로 직접 넘긴다.
        $json = $Body | ConvertTo-Json -Compress
        $args['Body']        = [Text.Encoding]::UTF8.GetBytes($json)
        $args['ContentType'] = 'application/json; charset=utf-8'
    }

    # PowerShell 5.1은 4xx·5xx를 예외로 던진다. 응답 객체에서 코드를 꺼낸다.
    try {
        $res    = Invoke-WebRequest @args
        $code   = [int]$res.StatusCode
        $content = $res.Content
    } catch [System.Net.WebException] {
        $resp = $_.Exception.Response
        if (-not $resp) { throw }
        $code = [int]$resp.StatusCode
        $reader = New-Object IO.StreamReader($resp.GetResponseStream(), [Text.Encoding]::UTF8)
        $content = $reader.ReadToEnd()
        $reader.Close()
    }

    $ok = ($code -eq $Expect)
    $parsed = $null
    if ($content) {
        try { $parsed = $content | ConvertFrom-Json } catch { $parsed = $null }
    }

    $result = [PSCustomObject]@{
        Grade   = $Grade
        Label   = $Label
        Method  = $Method
        Path    = $Path
        Expected = $Expect
        Actual  = $code
        Passed  = $ok
        Parsed  = $parsed
    }
    Write-Host ("{0}  {1,-4} 기대 {2} / 실제 {3}  {4}  {5}" -f `
        $Grade, $Method, $Expect, $code, $(if ($ok) { 'PASS' } else { 'FAIL' }), $Label) `
        -ForegroundColor $(if ($ok) { 'Green' } else { 'Red' })
    return $result
}

Write-Host ''
Write-Host '게시판 보안 API 응답 코드 확인' -ForegroundColor White
Write-Host ("대상: {0}   학생: {1}   (API 키는 .env에서 읽었고 화면에 찍지 않습니다)" -f $BaseUrl, $Student) -ForegroundColor DarkGray

$auth = @{ 'X-API-Key' = $ApiKey }
$results = @()

# D1 — 키가 없으면 들어올 수 없다.
$results += Invoke-Case -Label 'D1  API 키 없이 저장 시도' -Grade 'D1' -Expect 401 `
    -Method 'POST' -Path '/api/security/events' `
    -Body @{ student = $Student; src_ip = $DemoIp; decision = 'deny' }

# D2 — 키가 있어도 필수값이 빠지면 거절한다.
$results += Invoke-Case -Label 'D2  decision을 빠뜨리고 저장 시도' -Grade 'D2' -Expect 400 `
    -Method 'POST' -Path '/api/security/events' -Headers $auth `
    -Body @{ student = $Student; src_ip = $DemoIp }

# D3 — 제대로 갖추면 저장된다.
$results += Invoke-Case -Label 'D3  정상 저장' -Grade 'D3' -Expect 201 `
    -Method 'POST' -Path '/api/security/events' -Headers $auth `
    -Body @{
        student = $Student; src_ip = $DemoIp; decision = 'deny'
        severity = 'High'; fail_count = 12; window_min = 10
        # ConvertTo-Json이 '>'를 >로 바꿔 화면에 지저분하게 찍힌다. 문구에서 뺀다.
        reason = 'level 10 rule 5712 deny'
        source = 'api_demo'
    }

# D5 — 학생 이름으로 조회한다.
$results += Invoke-Case -Label 'D5  학생 이름으로 조회' -Grade 'D5' -Expect 200 `
    -Method 'GET' -Headers $auth `
    -Path ("/api/security/events?student={0}&limit=5" -f [Uri]::EscapeDataString($Student))

Write-Host ''
Write-Host ("=" * 72) -ForegroundColor DarkGray
$pass = ($results | Where-Object { $_.Passed }).Count
if ($pass -eq $results.Count) {
    Write-Host (" 전부 통과 — {0}/{1}" -f $pass, $results.Count) -ForegroundColor Green
} else {
    Write-Host (" 통과 {0}/{1} — 위에서 FAIL을 보세요" -f $pass, $results.Count) -ForegroundColor Red
}
Write-Host ("=" * 72) -ForegroundColor DarkGray
Write-Host ''
Write-Host ("D3 응답: id={0}, decision={1}, student={2}" -f `
    $results[2].Parsed.id, $results[2].Parsed.decision, $results[2].Parsed.student)
Write-Host ("D5 응답: count={0}, 첫 행={{id:{1}, decision:{2}, student:{3}}}" -f `
    $results[3].Parsed.count, $results[3].Parsed.events[0].id, `
    $results[3].Parsed.events[0].decision, $results[3].Parsed.events[0].student)
Write-Host 'API 키는 .env에서만 읽었으며 화면에는 표시하지 않았습니다.' -ForegroundColor DarkGray
Write-Host ''
