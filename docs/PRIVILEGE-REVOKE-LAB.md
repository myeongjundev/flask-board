# 자동 권한 회수봇 실습 — 이 환경 기준

준비일: 2026-09-16

수업 자료는 `E:\0-Aleph-Python-Test\Python-Lab-ALeph-T\_7_board_test`와 `lsy` 계정을
기준으로 쓰여 있다. 이 문서는 같은 실습을 이 PC에서 그대로 돌리기 위한 값과 명령을
모아 둔 것이다. 터미널은 PowerShell을 쓴다.

## 0. 이 환경의 값

| 항목 | 값 |
| --- | --- |
| 작업 폴더 | `C:\SKT aleph\flask-board` |
| 게시판 | http://localhost:5000 (`.venv\Scripts\python.exe app.py`) |
| MySQL | 도커 `flask_mysql` · 3306 · DB `my_new_board_db` |
| compose 프로젝트 | `skt-board` (`.env`의 `COMPOSE_PROJECT_NAME`) |
| Graylog | http://localhost:9000 (`gl-graylog`) · GELF 12201 |
| n8n | http://localhost:5678 (`n8n`) |
| 허용목록 | `zz_admin,instructor` (`.env`의 `ADMIN_ALLOWLIST`) |
| 관리자 키 | `.env`의 `ADMIN_API_KEY` — 문서·깃에 값을 적지 않는다 |

### 계정 매핑

| 수업 자료 | 이 환경 | 등급 | 비고 |
| --- | --- | --- | --- |
| `lsy` | `zz_admin` | 관리자(2) | 허용목록에 있어 회수 대상이 아니다 |
| `lsy2` | `zz_victim` | 관리자(2) | **과잉권한 — 회수 대상** |
| `lsy3` | `zz_gold` | 골드(1) | |
| `test1` | `zz_normal` | 일반(0) | |

비밀번호는 넷 다 `pw12345!`. 모두 합성 테스트 계정이다.

`zz_admin`을 지우거나 강등하지 않는다. 유일한 관리자가 되면 회수 API가
`마지막 관리자는 강등할 수 없습니다`(400)로 막아 E2E가 돌지 않는다.

## 1. 수업 자료와 다른 점

구현이 자료와 다른 부분이 있다. 명령을 그대로 옮겨 쓰면 막히는 지점들이다.

- **역할이 정수다.** `0`=일반, `1`=골드, `2`=관리자. 응답도 `role: 2`,
  `role_name: "관리자"`로 온다. 부여 API는 `user|gold|admin`과 `0|1|2`를 모두 받는다.
- **공용 판정기 파일명이 `controllers/authz.py`다.** 자료의 `rbac.py`에 해당하고,
  데코레이터 이름은 `api_role_required` / `page_role_required`다.
- **`/api/gold/posts`가 없다.** 골드는 `/gold` 페이지를 `@gold_page_required`로 막는
  방식이다. 자료 4-7의 API 403/401 검증을 그대로 하려면 `gold_controller.py`를
  따로 만들어야 한다.
- **회수 API는 `decision`과 `fail_count`를 읽지 않는다.** 각각 `deny`, `0`으로 고정
  기록된다. 읽는 값은 `username`(필수), `reason`, `student`, `src_ip`, `severity`,
  `source`, `generated_at`.

## 2. 점검 순서 (PowerShell)

### 준비 — 키를 변수에 담는다

```powershell
$KEY = ((Select-String -Path "C:\SKT aleph\flask-board\.env" -Pattern '^ADMIN_API_KEY=').Line -split '=',2)[1]
$h = @{ "Content-Type" = "application/json"; "X-API-Key" = $KEY }
```

### 0. 인프라 기동 확인

```powershell
docker ps --format "{{.Names}} | {{.Status}}"
Test-NetConnection -ComputerName 127.0.0.1 -Port 3306 -InformationLevel Quiet
```

`flask_mysql` · `gl-graylog` · `n8n`이 모두 Up이어야 한다. MySQL이 내려가 있으면:

```powershell
docker compose up -d
```

### 1. 게시판 기동

```powershell
Set-Location "C:\SKT aleph\flask-board"
.\.venv\Scripts\python.exe app.py
```

시작할 때 `_ensure_schema()`가 `users` 표에 `role` 계열 컬럼을 자동으로 채운다.

### 2. 계정 준비 (처음 한 번)

```powershell
foreach ($u in "zz_admin","zz_victim","zz_normal","zz_gold") {
  $body = @{ username = $u; password = "pw12345!" } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/api/auth/register" -Method POST -ContentType "application/json" -Body $body
}
```

부트스트랩 관리자와 골드를 만든다.

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/admin/grant" -Method POST -Headers $h -Body (@{ username="zz_admin"; role="admin"; reason="bootstrap admin" } | ConvertTo-Json)
Invoke-RestMethod -Uri "http://localhost:5000/api/admin/grant" -Method POST -Headers $h -Body (@{ username="zz_gold"; role="gold"; reason="class demo gold" } | ConvertTo-Json)
```

`reason`은 영문으로 쓴다. PowerShell/Git Bash에서 한글을 본문에 직접 넣으면 인코딩이
깨져 `username과 role이 필요합니다` 오류가 난다.

### 3. 과잉권한 재현

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/admin/grant" -Method POST -Headers $h -Body (@{ username="zz_victim"; role="admin"; reason="granted by mistake" } | ConvertTo-Json)
```

관리자 페이지에서도 같은 일을 할 수 있다. http://localhost:5000/admin 에 `zz_admin`
으로 로그인 → 권한 부여 칸에 `zz_victim` + `admin`.

### 4. 위반 조회

```powershell
$v = Invoke-RestMethod -Uri "http://localhost:5000/api/admin/violations" -Headers @{ "X-API-Key" = $KEY }
"허용목록: $($v.allowlist -join ', ')  위반: $($v.count)"
$v.violations | ForEach-Object { "   - $($_.username) ($($_.role_name))" }
```

`zz_victim` 1건이 나와야 한다. 0건이면 `ADMIN_ALLOWLIST`를 확인한다. 비어 있으면
모든 관리자가 위반으로 잡히고, 대상이 목록에 들어 있으면 제외된다.

### 5. 봇 탐지

```powershell
$env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe privilege_revoke_bot.py --dry-run
```

```text
[!] 과잉권한 관리자 1건 탐지: zz_victim
```

### 6. 봇 신고 → Graylog 수집

```powershell
.\.venv\Scripts\python.exe privilege_revoke_bot.py
```

```powershell
$b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin"))
$gh = @{ "Authorization" = "Basic $b64"; "Accept" = "application/json"; "X-Requested-By" = "cli" }
$r = Invoke-RestMethod -Uri "http://localhost:9000/api/search/universal/relative?query=rule:priv-unauthorized-admin&range=900&limit=5" -Headers $gh
"total_results: $($r.total_results)"
$r.messages | ForEach-Object { "  user=$($_.message.user) rule=$($_.message.rule) granted_by=$($_.message.granted_by)" }
```

`Accept: application/json`이 없으면 CSV 익스포터로 라우팅돼 `must not be empty`
오류가 난다.

### 7. n8n 없이 회수 경로만 검증

```powershell
$body = @{ username="zz_victim"; student="Kim Myeongjun"; severity="High"; src_ip="127.0.0.1"; reason="unauthorized admin auto-revoked via n8n" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5000/api/admin/revoke" -Method POST -Headers $h -Body $body
```

`old_role=2 → new_role=0`, `revoked=true`, `event_id`가 돌아온다. 이미 일반이면
`revoked=false`로 조용히 통과한다(멱등).

### 8. 전 구간 자동 회수

`zz_victim`을 다시 관리자로 만든 뒤 봇을 실행하고, 약 60초 기다린다.
Graylog 이벤트 스케줄러가 60초 주기로 돈다.

```powershell
for ($i = 0; $i -lt 12; $i++) {
  $u = Invoke-RestMethod -Uri "http://localhost:5000/api/admin/users?role=admin" -Headers @{ "X-API-Key" = $KEY }
  $names = ($u.users | ForEach-Object { $_.username }) -join ", "
  "$(Get-Date -Format HH:mm:ss)  admin: $names"
  if (-not ($u.users | Where-Object { $_.username -eq "zz_victim" })) { "  >>> 자동 회수 성공"; break }
  Start-Sleep -Seconds 10
}
```

### 9. 대시보드

http://localhost:5000/dashboard — `source=privilege-guard`, 판정 `거부` 행이 쌓인다.

## 3. 검증 상태 (2026-09-16)

| 구간 | 상태 |
| --- | --- |
| ① 봇 탐지 | 통과 |
| ② Graylog 수집(GELF) | 통과 — `total_results: 1` |
| ③ 이벤트 매치·필드 추출 | 통과 — `user`·`src_ip`·`granted_by` |
| ③ Notification → n8n | 설정 완료 (전송 성공, 수신 측 미완성) |
| ④ n8n 판정 | **미완성 — 워크플로가 비활성** |
| ⑤ 게시판 회수 | 통과 — `old_role=2 → new_role=0` |
| ⑥ 대시보드 | 통과 |

`POST /webhook/priv-guard`가 404인 동안은 전 구간이 완주하지 않는다.

## 4. 오늘 걸린 함정

### 이벤트는 걷히는데 회수가 안 된다 — Notification URL

Graylog 컨테이너 안에서 `localhost`는 컨테이너 자신이다. n8n은 호스트에 있으므로
닿지 않는다.

```text
Error: Failed to connect to localhost/[0:0:0:0:0:0:0:1]:5678
```

`http://host.docker.internal:5678/webhook/priv-guard`로 바꾼다. System ▸ Configurations ▸
URL Whitelist도 같은 주소로 고쳐야 한다. 확인 방법:

```powershell
docker exec gl-graylog sh -c "curl -s -o /dev/null -w '%{http_code}\n' --max-time 5 http://host.docker.internal:5678/"
```

### 알림은 가는데 아무 일도 안 일어난다 — `user` 필드 누락

이벤트 정의의 Fields에 `user`가 없으면 Notification body의 `${event.fields.user}`가
빈 값이 되고, n8n 판정 코드가 `if (!user) continue`로 전부 건너뛴다. 에러도 실행
기록도 남지 않아 찾기 어렵다. Fields에 `user`·`src_ip`·`granted_by`를 모두 등록한다.

### 이벤트 자체가 안 걷힌다 — `_rule` vs `rule`

GELF 커스텀 필드는 색인될 때 앞의 `_`가 벗겨진다. 봇이 `_rule`로 보내도 검색·필터
쿼리는 `rule:priv-unauthorized-admin`이라야 한다.

### 그 밖

- 회수까지 약 60초 지연되는 것은 정상이다(이벤트 스케줄러 주기).
- 디스코드 웹훅은 `User-Agent` 헤더가 없으면 Cloudflare가 `1010`으로 막는다.
- 알림 Content-Type은 enum `JSON`이다. `application/json` 문자열은 거부된다.

## 5. 남은 작업

- [ ] n8n `자동 권한 회수봇 graylog 연동` 워크플로 완성 (판정 코드·Webhook path
      `priv-guard`·HTTP Request·Active 토글)
- [ ] 작업 스케줄러 `PrivilegeRevokeBot` 등록 (매시간) — 현재 미등록
- [ ] 전 구간 E2E 완주 후 캡처

## 6. 안전

- 합성 계정(`zz_` 접두사)만 쓴다. 실명·PII를 넣지 않는다.
- `ADMIN_API_KEY`·`SECURITY_API_KEY`·웹훅 URL·토큰은 `.env`와 n8n 노드에만 둔다.
  이 문서를 포함해 어떤 문서에도 실값을 적지 않는다.
- Graylog `admin/admin`과 OpenSearch 보안 비활성화는 로컬 실습 전용이다.
- 회수봇은 이 PC의 게시판만 대상으로 한다.
