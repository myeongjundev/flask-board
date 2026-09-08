# [초안] 제출용 README

> **이 파일은 초안입니다.** 내용을 확정한 뒤 저장소 루트 `README.md`로 옮기세요.
> 별도 파일로 둔 이유는 코덱스가 `README.md`를 동시에 편집할 수 있어서입니다.
>
> **채우셔야 하는 곳은 `⟨...⟩`로 표시했습니다.** 특히 ③ 이미지와 ⑤ 막혔던 점은
> 실제 겪은 일이어야 합니다.

---

# 로그인 경보 자동화 봇

파이썬이 보낸 로그인 경보를 **n8n이 스스로 판단(허용/거부)** 하고, 그 결과를
**메신저로 알린 뒤 게시판 DB에 기록**하는 자동화 봇입니다. 판단 기준은 n8n Code
노드의 상수 하나로 모여 있어, 숫자만 바꾸면 허용이던 경보가 거부로 바뀝니다.

기존에 만들던 Flask 게시판에 보안 이벤트 REST API와 대시보드를 덧붙여, 자동화의
결과가 사람이 볼 수 있는 화면까지 이어지게 했습니다.

```text
[내 PC · 파이썬]              [Docker · n8n]                  [Docker · MySQL]
alert_sender.py                                                my_new_board_db
     │                                                               ▲
     │ ① HTTP POST (JSON)                                            │
     ▼                                                               │
  Webhook → Code(판정) → IF(deny?)                                    │
                          ├─ 🚫 거부 문구 ─┬─▶ 슬랙·디스코드·텔레그램   │
                          └─ ✅ 허용 문구 ─┘                          │
                                          └─▶ 게시판 저장 ── ③ REST ──┘
```

## ② 작업 내역

### 만든 순서

1. **게시판 정리** — 실습 파일 14개를 `config.py` · `models/` · `controllers/`로
   나누고, 설정값을 전부 `.env`로 뺐습니다.
2. **보안 이벤트 모델·API** — `security_events` 테이블과
   `POST/GET /api/security/events`를 만들었습니다. 저장은 `X-API-Key`로 막았습니다.
3. **파이썬 전송기** — `alert_sender.py`에서 거부될 경보(level 10)와 허용될
   경보(level 3)를 함께 보냅니다.
4. **n8n 워크플로** — Webhook → Code(판정) → IF(분기) → 메신저 3곳 + 게시판 저장.
5. **대시보드** — `/dashboard`에서 n8n이 저장한 허용·거부 결과를 확인합니다.

### 사용한 것

| 구분 | 사용 |
| --- | --- |
| 언어 | Python 3.13 |
| 웹 | Flask 3.1, Flask-SQLAlchemy, Flask-JWT-Extended |
| 자동화 | n8n (Docker) — Webhook · Code(JavaScript) · IF · HTTP Request |
| DB | MySQL 8.0 (Docker), 스키마 `my_new_board_db` |
| 메신저 | ⟨실제로 연결한 것을 적으세요: 슬랙 / 디스코드 / 텔레그램⟩ |
| 기타 | python-dotenv, requests, pytest |

### 판정 규칙

거부 기준은 Code 노드 맨 위 `DENY_LEVEL` 상수 하나입니다.

| 조건 | severity | decision |
| --- | --- | --- |
| level ≥ 10 | High | **deny** |
| level ≥ 7 | Medium | allow |
| 그 외 | Low | allow |

## ③ 기능 구현 화면

> 아래 표의 캡처를 `images/` 폴더에 넣고 파일명을 맞추면 그대로 표시됩니다.
> **토큰·Webhook 주소가 화면에 찍히지 않았는지 확인하세요.**

### n8n 워크플로 전체

![n8n 워크플로](images/01-n8n-workflow.png)

### 실행 성공 — 노드가 모두 초록

![n8n 실행 성공](images/02-n8n-execution.png)

### Code 노드 출력 — 경보 2건이 아이템 2개로

![Code 노드 출력](images/03-code-output.png)

### 메신저 도착

![슬랙](images/04-slack.png)
![디스코드](images/05-discord.png)
![텔레그램](images/06-telegram.png)

### 데이터베이스 저장 결과

![MySQL](images/07-mysql.png)

### 대시보드

![대시보드](images/08-dashboard.png)

### 파이썬 전송기 실행

![alert_sender 실행](images/09-sender.png)

---

<details>
<summary>캡처 목록과 배점 대응 (제출 전 확인용 — 확정 후 지워도 됩니다)</summary>

| 파일명 | 무엇을 찍나 | 배점 항목 |
| --- | --- | --- |
| `01-n8n-workflow.png` | 노드가 연결된 캔버스 전체 | C1 |
| `02-n8n-execution.png` | IF 양쪽 갈래가 모두 초록인 실행 | C1 · D6 |
| `03-code-output.png` | Code 노드 OUTPUT — 아이템 2개, `decision`·`severity`·`reason` | B1 · B2 |
| `04-slack.png` | 슬랙에 🚫거부 + ✅허용 두 건 | C2 · C5 |
| `05-discord.png` | 디스코드에 두 건 | C3 |
| `06-telegram.png` | 텔레그램에 두 건 | C4 |
| `07-mysql.png` | `SELECT ... FROM security_events` — 본인 이름, deny·allow 각 1건 | D4 |
| `08-dashboard.png` | `/dashboard` 화면 | (가점) |
| `09-sender.png` | `alert_sender.py` 실행 → `200` | A1 · A2 |
| `10-deny-level-3.png` | `DENY_LEVEL`을 3으로 바꾼 뒤 판정이 달라진 화면 | B3 |
| `11-api-401-400-201.png` | 키 없이 401 · 필수값 누락 400 · 정상 201 | D1 · D2 · D3 |
| `12-get-events.png` | `GET /api/security/events?student=...` 응답 | D5 |

</details>

## ④ 실행 방법

### ① 켜는 것

```powershell
docker start n8n flask_mysql     # n8n(5678), MySQL(3306)
Copy-Item .env.example .env      # 처음 한 번만. 실제 값을 채운다
pip install -r requirements.txt
python app.py                    # 게시판 5000번
```

n8n 화면(`http://localhost:5678`)에서 워크플로를 **Active**로 켭니다.

### ② 실행하는 것

```powershell
python alert_sender.py
```

### ③ 무엇이 보이면 통과인가

- 터미널에 `[n8n] POST -> 200`
- n8n Executions에서 **IF 양쪽 갈래가 모두 초록**, `게시판 저장` 노드 응답 `201`
- 메신저에 🚫거부 1건 + ✅허용 1건 도착
- `http://127.0.0.1:5000/dashboard`에 두 줄이 보임
- MySQL에서 `SELECT * FROM security_events`에 deny·allow 각 1건

### ④ 안 될 때 보는 곳

| 증상 | 볼 곳 |
| --- | --- |
| n8n이 404 | 워크플로가 Active인가. 주소가 `webhook-test`인가 `webhook`인가 |
| Code 노드가 바로 실패 | 오류 문구를 그대로 읽는다. 언어 선택 문제일 수 있다 (⑤ 참고) |
| 판정 결과가 비어 있음 | Webhook이 받은 데이터가 `body` **아래**에 들어간다. OUTPUT 패널 확인 |
| 메신저에 `{{ }}`가 그대로 | 입력칸이 표현식 모드인지 확인 |
| 게시판 저장이 연결 거부 | 컨테이너 안에서 `localhost`는 컨테이너 자신이다 (⑤ 참고) |
| 게시판 저장이 401 | `X-API-Key` 헤더 이름과 값이 `.env`의 `SECURITY_API_KEY`와 같은가 |
| 게시판 저장이 400 | 앞 노드에서 `src_ip` 등 원본 필드가 사라지지 않았는가 |

## ⑤ 막혔던 점과 해결

### 1. n8n 컨테이너에서 게시판에 연결이 되지 않았다

**증상** — 게시판 저장 노드가 연결 거부로 실패했습니다.

**원인** — n8n은 Docker 컨테이너 안에서 돌고 게시판은 호스트(내 PC)에서 돕니다.
컨테이너 안에서 `localhost:5000`은 **컨테이너 자기 자신의 5000번**이라, 거기엔
아무것도 없습니다.

**해결** — HTTP Request 노드의 주소를
`http://host.docker.internal:5000/api/security/events`로 바꿨습니다.

### 2. DB에 한 줄도 쌓이지 않았다

**증상** — 테이블은 만들어졌는데 `SELECT COUNT(*)`가 계속 `0`이었습니다.

**원인** — 게시판 서버(5000번)가 꺼져 있었습니다. n8n은 저장 요청을 보냈지만 받을
쪽이 없었습니다. n8n 실행 기록만 보고 "저장했다"고 넘기면 놓치는 지점입니다.

**해결** — `python app.py`로 게시판을 먼저 띄운 뒤 다시 실행했고, `201`과 함께
`id`가 돌아오는 것을 확인했습니다. 이후 **DB를 직접 조회해서** 확인하는 것을
절차에 넣었습니다.

### 3. ⟨Code 노드 언어 함정 — 실제로 겪은 일을 적으세요⟩

문제지 B4 배점 항목입니다.

- **무슨 일이 있었나:** ⟨어떤 언어를 골랐고 어떤 오류가 났는지⟩
- **원인:** ⟨왜 그랬는지⟩
- **어떻게 해결했나:** ⟨무엇으로 바꿨는지⟩

> 참고: 현재 워크플로는 **JavaScript**에 `Run Once for All Items`로 되어 있습니다.
> Python(Beta)을 골랐다면 `$input`·`items` 사용법이 다르고 일부 노드 표현식이
> 그대로 통하지 않습니다.

## AI 활용 구분

> 문제지 E4 항목입니다. **직접 쓰셔야 합니다** — 채점자가 커밋 기록과 대조합니다.

- **AI에게 맡긴 일:** ⟨예: 게시판 구조 분리, API 초안, 테스트 작성⟩
- **내가 직접 판단한 일:** ⟨예: 판정 기준을 상수로 뺀 것, 키를 .env로 분리한 것⟩
- **AI 제안을 따르지 않은 일:** ⟨없으면 없다고 쓰고 이유를 적으세요⟩

## 보안

- Webhook 주소·봇 토큰·API 키·DB 비밀번호는 **`.env`에만** 둡니다. 저장소에는 값이
  없는 `.env.example`만 있습니다.
- 메신저 Webhook과 봇 토큰은 소스가 아니라 **n8n Credential**에 넣었습니다.
- 테스트 데이터는 예약 대역(`1.2.3.114`, `192.168.0.10`)만 씁니다. 실제 사람의
  계정·이메일·전화번호를 쓰지 않습니다.
- ⟨노출된 값을 재발급했다면 여기에 적으세요⟩

## 심화 (S1)

`GET /api/security/events/summary?student=<이름>`으로 허용·거부 건수와 거부가 많은
상위 IP를 함께 봅니다.

```json
{ "student": "...", "by_decision": {"allow": 1, "deny": 1},
  "top_deny_ips": [{"src_ip": "1.2.3.114", "fails": 20}] }
```
