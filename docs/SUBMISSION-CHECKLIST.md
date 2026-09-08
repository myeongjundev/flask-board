# 로그인 경보 자동화 봇 제출 체크리스트

확인일: 2026-09-08

표시 기준:

- `[x]` 기능과 제출 증적 파일이 모두 준비됨
- `[△]` 기능은 검증됐지만 캡처 파일이 아직 없음
- `[ ]` 추가 실행 또는 보안 조치가 필요함

## A. 파이썬 전송기

- [△] A1 — n8n 응답 200 확인. `images/09-sender.png` 캡처 필요
- [△] A2 — `student`와 경보 2건 전송 확인. `images/09-sender.png`에 함께 표시
- [△] A3 — n8n 중지 시 안전한 오류 메시지 후 정상 종료 확인. 실패 화면 캡처 필요

## B. n8n 판정

- [△] B1 — 최신 실행에서 Code 출력 2개 확인. `images/03-code-output.png` 필요
- [△] B2 — level 10은 deny/High, level 3은 allow/Low 확인. 위 이미지에 함께 표시
- [△] B3 — `DENY_LEVEL` 10과 3의 두 실행 비교 완료. 기준은 10으로 복원함.
  `images/10-deny-level-3.png` 캡처 필요
- [x] B4 — Python runner 오류 원인과 JavaScript 전환을 제출문 초안에 기록

## C. 분기와 메신저

- [x] C1 — `images/02-n8n-execution.png`에서 IF 양쪽 갈래와 전체 노드 성공 확인
- [x] C2 — `images/04-slack.png`
- [x] C3 — `images/05-discord.png`
- [x] C4 — `images/06-telegram.png`
- [x] C5 — 세 이미지에서 거부(🚫)와 허용(✅) 형식 차이 확인

## D. 게시판 REST와 DB

- [△] D1 — 키 없이 POST 401 확인. API 검증 화면 캡처 필요
- [△] D2 — 필수값 누락 POST 400 확인. API 검증 화면 캡처 필요
- [△] D3 — 정상 POST 201과 id 반환 확인. API 검증 화면 캡처 필요
- [△] D4 — MySQL에 `login_alert_lab` deny·allow 각 1건 이상 확인.
  `images/07-mysql.png` 필요
- [△] D5 — 학생별 GET 200 확인. API 검증 화면 캡처 필요
- [△] D6 — `images/02-n8n-execution.png`에서 게시판 저장 노드 성공은 확인.
  노드 OUTPUT의 응답 `201`이 보이는 캡처 필요

## E. 안전과 제출 무결성

- [x] E1 — 현재 추적 파일과 전체 Git 기록을 정밀 스캔해 실제 메신저 Webhook·봇
  토큰·API 키·DB 비밀번호 원문 0건 확인. 제출 이미지에도 비밀값 원문 없음
- [x] E2 — 워크플로 Export 파일은 제출물에 포함하지 않음. 추후 포함한다면 비밀 URL과
  Credential 값을 `<REDACTED>`로 치환
- [x] E3 — 실행 순서 4단계를 `README.md`에 작성
- [x] E4 — AI 활용 구분 3항목을 `README.md`에 작성

## 심화

- [x] S1 — 학생별 허용·거부 요약과 거부 상위 IP API 구현·테스트 및
  `images/08-dashboard.png` 증적 준비
- [△] S4 — 5분 작업 스케줄러 등록 및 반복 성공 확인 후 메시지 중복 방지를 위해 해제.
  제출 가산점은 증적이 준비된 S1로 충족

## 최종 제출 직전

- [ ] 빠진 캡처를 `images/`에 추가
- [ ] 모든 이미지에서 Webhook URL·봇 토큰·API 키·DB 비밀번호가 안 보이는지 재확인
- [x] 제출문 초안을 최종 검토해 루트 `README.md`에 반영
- [x] `python -m pytest -q` 결과가 `8 passed`
- [ ] 변경사항 커밋·푸시
- [x] 반복 메시지 방지를 위해 `scripts/unregister_alert_task.ps1` 실행
