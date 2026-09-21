# flask-board 위치 변경 체크리스트

이 문서는 프로젝트 폴더나 PC가 바뀌어도 Flask, MySQL, n8n, Graylog, Kali,
Discord 연동을 같은 순서로 복구하기 위한 실행 템플릿이다.

## 왜 폴더 복사만으로 끝나지 않는가

설정은 한곳에 있지 않다.

| 구성 요소 | 설정 저장 위치 | 위치 변경 시 확인할 값 |
|---|---|---|
| Flask | 프로젝트 `.env` | DB URL, 학생명, API 키, Webhook URL |
| MySQL | Docker 볼륨 | 기존 테이블 형식과 데이터 |
| n8n | n8n Docker 볼륨 | Webhook 경로, API 키, 메신저 URL |
| Graylog | Graylog/Mongo 볼륨 | 알림 대상 URL과 GELF 입력 |
| Kali | `portcheck2.sh` | Windows IP, 학생명, n8n 주소 |
| Windows 작업 스케줄러 | Windows 시스템 | Python, 스크립트, 작업 폴더의 절대 경로 |

## 1. 이동 전에 백업

프로젝트 루트에서 다음 명령을 실행한다. 기본 실행은 설정을 변경하지 않고 n8n을
`backups/n8n/<날짜>`에 백업하고 현재 상태만 점검한다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\relocate_environment.ps1
```

백업 JSON에는 Discord/Slack/Telegram Webhook과 API 키가 포함될 수 있다.
`backups/n8n/`은 Git에서 제외되며 외부에 공유하면 안 된다.

## 2. 새 위치에서 `.env` 확인

`.env.example`을 기준으로 아래 항목이 실제 값인지 확인한다.

```env
DATABASE_URL=mysql+pymysql://<계정>:<비밀번호>@localhost:3306/my_new_board_db
JWT_SECRET_KEY=<랜덤 값>
SECURITY_API_KEY=<n8n 게시판 저장 노드와 같은 값>
ADMIN_API_KEY=<n8n 관리자 대응 노드와 같은 값>
STUDENT_NAME=myeongjundev
BOARD_URL=http://localhost:5000
GELF_HOST=localhost
N8N_WEBHOOK_URL=http://localhost:5678/webhook/<운영 경로>
DISCORD_WEBHOOK_NAME=Spidey Bot
SLACK_WEBHOOK_URL=<현재 Slack 채널의 새 Incoming Webhook URL>
TELEGRAM_BOT_TOKEN=<현재 Telegram 봇의 BotFather 토큰>
TELEGRAM_CHAT_ID=<현재 개인 또는 그룹 chat_id>
```

Slack/Telegram 값을 비워 두면 n8n에 이미 저장된 기존 목적지를 그대로 유지한다.
새 목적지로 바꿀 때만 세 값을 채운다.

컨테이너에서 Windows Flask를 호출할 때는 `localhost`가 아니라 다음 주소를 쓴다.

```text
http://host.docker.internal:5000
```

## 3. Python 환경 복구

```powershell
Set-Location <새 프로젝트 경로>
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe app.py
```

확인 주소:

- Flask: `http://localhost:5000/`
- 대시보드: `http://localhost:5000/dashboard`
- n8n: `http://localhost:5678`
- Graylog: `http://localhost:9000`

## 4. n8n 일괄 갱신

Flask와 Docker 서비스가 실행된 상태에서 적용한다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\relocate_environment.ps1 `
  -Apply -RunTest -DiscordWebhookName "Spidey Bot"
```

`-RunTest`의 합성 포트 점검 대상은 기본적으로 `127.0.0.1`이다. 새 PC의 실제
LAN 주소를 증적에 남기려면 `-TestHost 192.168.x.x`를 추가한다.

스크립트가 수행하는 작업:

1. 현재 워크플로를 로컬에 백업한다.
2. `lsy` 같은 이전 학생명을 `.env`의 `STUDENT_NAME`으로 바꾼다.
3. Flask 호출 주소를 `host.docker.internal:5000`으로 통일한다.
4. 게시판 저장에는 `SECURITY_API_KEY`, 관리자 대응에는 `ADMIN_API_KEY`를 넣는다.
5. 이름이 정확히 `Spidey Bot`인 Discord Webhook을 찾아 모든 Discord 노드에 적용한다.
6. `.env`의 새 Slack Webhook과 Telegram 봇 토큰·chat ID를 모든 노드에 적용한다.
7. `/webhook/vuln-scan`을 등록하고 워크플로를 재게시한다.
8. n8n을 재시작하고 로그인 경보 및 포트 점검 E2E 요청을 보낸다.

## 5. Kali 포트 점검 스크립트

저장소의 `scripts/portcheck2.sh`를 Kali에 복사한 뒤 실행한다.

```bash
chmod +x portcheck2.sh
./portcheck2.sh 192.168.3.14
```

Windows IP가 바뀌면 마지막 인자만 바꾼다. 학생명은 기본적으로
`myeongjundev`이며 필요하면 `STUDENT_NAME` 환경변수로 덮어쓴다.

## 6. 완료 판정

아래가 모두 만족돼야 이전이 완료된 것이다.

- `GET http://localhost:5678/healthz`가 200이다.
- `/webhook/vuln-scan`이 404가 아니라 200을 반환한다.
- n8n 실행 결과가 `success`다.
- Discord 발신자가 `Spidey Bot`이다.
- 대시보드에 현재 학생명으로 허용/거부 이벤트가 저장된다.
- `python -m unittest discover -s tests -q`가 모두 통과한다.
- 작업 스케줄러의 실행 파일과 작업 폴더가 이전 경로를 가리키지 않는다.

## 7. 자주 발생하는 오류

| 증상 | 원인 | 해결 |
|---|---|---|
| `POST vuln-scan is not registered` | 운영 Webhook 경로 불일치 또는 미게시 | 재배치 스크립트 `-Apply` 실행 |
| Flask 저장 노드 401 | n8n과 `.env`의 API 키 불일치 | API 키 일괄 갱신 |
| `Invalid Webhook Token` | 폐기된 Discord URL | `Spidey Bot` 이름으로 다시 적용 |
| 알림이 `Captain Hook`으로 감 | 다른 정상 Webhook을 선택함 | Webhook 이름까지 검증 |
| 컨테이너에서 Flask 연결 실패 | `localhost:5000` 사용 | `host.docker.internal:5000` 사용 |
| 문자열과 정수 권한 비교 오류 | 이전 DB의 `admin/user` 문자열 | 앱 시작 시 역할 마이그레이션 확인 |
| 화면에는 이전 오류가 남음 | n8n 편집기의 과거 실행 결과 | 저장하지 말고 새로고침 후 현재 게시 버전 확인 |

## 8. 롤백

문제가 생기면 가장 최근 `backups/n8n/<날짜>` 폴더를 컨테이너로 복사해 다시
가져온다. 가져오기 직후에는 각 워크플로를 다시 게시하고 n8n을 재시작해야 한다.
백업에는 비밀값이 있으므로 롤백 후에도 Git에 추가하지 않는다.
