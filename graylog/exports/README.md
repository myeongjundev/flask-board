# Graylog Alerts 설정 내보내기

실제 Graylog API에서 읽은 Event Definitions와 Notifications를 기록합니다.
각 폴더 이름은 내보낸 PC의 로컬 시각 `YYYYMMDD_HHMMSS`입니다. 이번 기록은 한국 시각입니다.

## 2026-10-08 기록

- [설정 목록·LLM 검토 요청문](20261008_124730/EVENT-DEFINITIONS.md)
- [Event Definitions 검토 JSON](20261008_124730/event-definitions.review.json): 시스템 기본 정의를 포함한 11개.
- [Notifications 검토 JSON](20261008_124730/notifications.review.json): 6개, 개인 URL·인증 정보 제거.
- [Content Pack JSON](20261008_124730/graylog-alerts.content-pack.json): 사용자 정의 10개, 연결 알림 6개와 Stream 이름 참조.
- [가져오기 및 개인 환경 설정](20261008_124730/README.md)

검토 JSON은 API 응답을 정리한 기록이며 Content Pack 업로드 형식이 아닙니다.
공유용 Content Pack은 대상 PC의 URL·인증을 입력하고 정의를 검토한 뒤 활성화하도록
비활성 상태로 저장했습니다. Stream 라우팅, n8n Workflow, Wazuh 규칙과 Agent 설정은
이 파일에 포함되지 않습니다.

## 다시 내보내기

게시판 루트에서 실행하고 Graylog 비밀번호를 입력합니다. 추가 패키지 없이 Python
표준 라이브러리로 실행되며 기존 탐지 정의·알림·활성 상태를 변경하지 않습니다.

```powershell
python .\scripts\export_graylog_alerts.py
```

공유본은 `graylog/exports/`, 비공개 원본 API 응답과 SHA-256 목록은
Git에서 제외된 `backups/graylog/`에 저장합니다. API가 숨긴 암호화된 비밀은 전체
복원이 보장되지 않으므로 대상 PC에서 인증 정보를 확인합니다.
