# 로그인 경보 게시판 실행 준비

## 1. 로컬 설정

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

출력한 랜덤 문자열을 `.env`의 `JWT_SECRET_KEY`와 `SECURITY_API_KEY`에 각각 다른
값으로 넣는다. `DATABASE_URL`에는 현재 사용하는 MySQL 계정과 비밀번호를 입력한다.
비밀번호에 `@`, `#`, `/`, `:`가 있으면 URL 인코딩한다.

`.env`와 실제 Webhook·토큰은 Git이나 캡처 화면에 넣지 않는다.

## 2. 게시판 실행

```powershell
python -m pip install -r requirements.txt
python app.py
```

확인 주소:

- 게시판: `http://localhost:5000/`
- 보안 대시보드: `http://localhost:5000/dashboard`
- 부산 테마여행: `http://localhost:5000/public-post`
- 보안 이벤트 조회: `http://localhost:5000/api/security/events?student=<본인 식별자>`

`db.create_all()`은 기존 `users`, `posts`를 유지하고 없는 `security_events` 테이블만
추가한다. 실제 실행 전에는 DB 백업 여부를 확인한다.

## 3. n8n 연결

n8n 컨테이너에서 Windows 호스트의 게시판으로 보낼 때 주소는 다음과 같다.

```text
http://host.docker.internal:5000/api/security/events
```

HTTP Request 노드에 `X-API-Key` 헤더를 추가하고 `.env`의 `SECURITY_API_KEY`와 같은
값을 n8n Credential에 저장한다. 워크플로 JSON을 내보낼 때 키가 포함되지 않았는지
반드시 확인한다.

상세 노드 구성은 `docs/N8N-WORKFLOW.md`를 따른다.

## 4. 전송기 실행

`.env`에 n8n의 활성화된 운영 Webhook URL과 본인 식별자를 설정한다.

```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook/<본인 경로>
STUDENT_NAME=<본인 식별자>
```

```powershell
python alert_sender.py
```

레벨 10의 거부 후보와 레벨 3의 허용 후보가 한 번에 전송된다. n8n이 꺼져 있거나
주소가 틀려도 전송기는 오류 메시지를 출력하고 정상적으로 종료한다.
