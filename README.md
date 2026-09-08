# Flask RESTful 게시판

제미나이 가이드 기반. JWT 인증 + 검색/필터 + 커서 기반 페이징.

## 2026-09-08 로그인 경보 자동화 확장

강사 실습의 구조분리 버전을 이 저장소에 맞게 통합했다.

- `config.py`: `.env`에서 DB·JWT·보안 API·공공데이터 설정 로드
- `models/`: 기존 사용자·게시글과 신규 `security_events` 모델
- `controllers/`: 화면·인증·게시글·보안 이벤트·부산 여행 요청 분리
- `/dashboard`: n8n이 저장한 허용·거부 결과 확인
- `POST /api/security/events`: `X-API-Key`로 보호된 저장 API
- `GET /api/security/events`: 학생별 최신 기록 조회
- `alert_sender.py`: deny/allow 판정용 합성 경보 두 건 전송

기존 `/public-post`, `/busan-travel` 주소와 게시글 데이터 구조는 유지한다.

## 현재 구성 (2차 최종)

2차 요구사항인 "기존 MySQL 서버에 접속해서 새 스키마를 생성해 사용"을 그대로 따른다.
게시판 전용 컨테이너를 띄우지 않고, 수업용으로 이미 돌고 있는 `mysql-lab`을 재사용한다.

- 서버: `mysql-lab` 컨테이너, 포트 **3306**, 접속 정보는 `.env`의 `DATABASE_URL`
- 스키마: `my_new_board_db` (utf8mb4 / utf8mb4_unicode_ci)
- 테이블: `users`, `posts` (SQLAlchemy가 자동 생성)
- 앱 포트: **5000** (`_6_test/app.py`도 5000을 쓰므로 동시에 띄울 수 없다)

같은 서버 안에 수업용 `github_db`가 함께 있다. 서로 독립이다.

## 실행

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
# .env의 DATABASE_URL, JWT_SECRET_KEY, SECURITY_API_KEY 등을 본인 값으로 수정
python app.py
```

접속: http://127.0.0.1:5000 (테스트 계정 `tester` / `pw1234`)

MySQL은 `mysql-lab` 컨테이너가 이미 떠 있으면 따로 할 일이 없다.

## 공공데이터 연동 — 부산 테마여행정보

부산광역시 부산테마여행정보 Open API의 국문 데이터를 서버에서 호출한다.
게시판 헤더의 `부산 테마여행` 메뉴에서 최대 100개 추천여행 목록을 보고,
콘텐츠를 눌러 주소·연락처·운영시간·이용요금·상세내용 화면으로 이동한다.

- 목록: http://127.0.0.1:5000/public-post
- 상세: `/public-post/<콘텐츠 ID>`
- 기존 `/busan-travel` 주소도 같은 화면의 별칭으로 유지한다.
- 공식 API: https://www.data.go.kr/data/15063506/openapi.do
- 요청주소: `https://apis.data.go.kr/6260000/RecommendedService/getRecommendedKr`

직접 호출 샘플(브라우저·Postman에서는 발급 화면의 일반 인증키 Encoding 값 사용):

```text
https://apis.data.go.kr/6260000/RecommendedService/getRecommendedKr?serviceKey=ENCODING_인증키&numOfRows=100&pageNo=1&resultType=json
```

콘텐츠 ID 305 상세 조회 샘플:

```text
https://apis.data.go.kr/6260000/RecommendedService/getRecommendedKr?serviceKey=ENCODING_인증키&numOfRows=1&pageNo=1&resultType=json&UC_SEQ=305
```

공공데이터포털에서 활용신청 후 발급 화면의 **일반 인증키(Decoding)** 값을 현재
PowerShell 세션의 환경변수로 설정한다. 키는 소스에 붙여 넣지 않는다.

```powershell
$env:DATA_GO_KR_SERVICE_KEY = "여기에_일반_인증키_Decoding_값"
python app.py
```

밑줄 입력이 불편하면 같은 기능의 짧은 변수명을 사용할 수 있다.

```powershell
$env:TOURKEY = Read-Host "인증키"
python app.py
```

새 터미널을 열면 환경변수를 다시 설정해야 한다. 코드 변경 후 서버를 다시 시작하고
`http://127.0.0.1:5000`의 헤더 메뉴를 누른다.

## docker-compose.yml について

1차 가이드대로 게시판 전용 MySQL(`flask_mysql`, 3307)을 띄우던 파일이다.
2차에서 3306의 `mysql-lab`으로 옮기면서 더 이상 쓰지 않는다.
컨테이너는 중지만 해둔 상태이므로 되살리려면 `docker compose start`.
완전히 정리하려면 `docker compose down -v` (볼륨까지 삭제, 되돌릴 수 없음).

## 원본 가이드에서 고친 것

1. **포트 충돌** — MySQL 3306은 `mysql-lab`, Flask 5000은 `_6_test`가 사용 중이었다.
   DB는 3306을 공유한다. 앱 포트는 5000으로 되돌렸으므로 `_6_test`와 동시 실행은 안 된다.
2. **`get_posts()`의 잡문자열** — 1차 붙여넣기에 `Under Construction`이 섞여 있어 제거.
   (2차 원문에는 없다. 복사 사고였다.)
3. **requirements 버전 고정 해제** — Python 3.14용 휠이 없어 `>=` 하한으로 변경.
4. **모달이 안 닫히는 버그** — 원본은 `class="... hidden flex ..."`라 `hidden`을 빼도
   항상 flex로 남았다. `showModal()`/`hideModal()`로 `hidden`↔`flex`를 함께 토글.
5. **XSS** — 수정/삭제 버튼을 `onclick` 문자열 조립 대신 `addEventListener`로 연결.
   원본 `escapeAttr`은 `<`, `&`를 처리하지 않아 제목에 태그를 넣으면 실행됐다.
   `category`, `author`에도 `escapeHtml` 적용.
6. **JWT 시크릿 키 연장** — 28바이트라 PyJWT가 경고를 냈다.
7. **collation** — 컨테이너 기본값이 `utf8mb4_0900_ai_ci`라 가이드 명세인
   `utf8mb4_unicode_ci`로 교정.

## 주의

DB 비밀번호, JWT 키, n8n Webhook, 보안 API 키와 공공데이터 키는 `.env`에만 둔다.
`.env.example`에는 키 이름과 예시 형식만 두고 실제 값은 넣지 않는다. 과거 커밋에 사용한
n8n Webhook은 제출 전에 폐기하고 새 Webhook으로 교체한다.
