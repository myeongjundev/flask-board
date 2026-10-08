# Graylog Alerts 내보내기

생성: 2026-10-08T12:47:30+09:00 / Graylog 6.1.16+4a05695

## 파일

- `EVENT-DEFINITIONS.md`: 실제 검색·집계 조건과 LLM 검토 요청문.
- `event-definitions.review.json`: 시스템 기본 항목을 포함한 정의 11개의 API 설정. 다른 PC에 직접 업로드하는 형식은 아닙니다.
- `notifications.review.json`: 알림 6개의 검토용 설정. URL·인증 헤더·인증 정보는 제거했습니다.
- `graylog-alerts.content-pack.json`: 사용자 정의 10개와 연결 Notification 6개, 필요한 의존성을 Catalog API로 내보낸 Content Pack입니다. 시스템 기본 정의는 대상 서버의 기본 항목을 사용합니다.

## 다른 PC에서 가져오기

1. 우선 대상 PC의 기존 설정을 내보내 기록하세요. Graylog 버전은 원본(6.1.16+4a05695)의 제약 조건을 만족해야 합니다.
2. 대상 Graylog의 `System > Content Packs`에서 `Upload`로 Content Pack JSON을 선택하세요. 업로드와 설치는 별도 단계입니다.
3. 설치 전에 필요한 Stream 이름을 확인하세요: Wazuh 경보. `stream_title`은 기존 Stream을 이름으로 참조하며 Stream 규칙을 새로 만드는 항목이 아닙니다.
4. `Install` 단계에서 Notification별 URL 파라미터에 **대상 PC의 실제 n8n Webhook URL**을 입력하세요. Docker 안에서 호스트의 n8n을 호출한다면 `localhost`가 아닌 실제 도달 가능한 주소를 사용하세요.
5. headers 파라미터의 기본값 `{}`에는 인증이 없습니다. 필요한 인증 헤더를 대상 PC에서 입력하고, 설치 후 Notifications의 Basic Auth / API Secret도 직접 확인하세요. 암호화된 비밀은 API/Content Pack으로 완전히 복원할 수 없습니다.
6. 이 공유 Pack의 Event Definitions는 모두 **비활성 상태**입니다. 원본의 ENABLED/DISABLED 상태는 검토 JSON에 보존되어 있습니다. 검색 Stream, Custom Fields, Notification 연결을 확인한 뒤 필요한 정의만 활성화하세요.
7. 실제 로그로 탐지 이벤트 생성 → Notification 호출 → n8n 실행을 각각 검증하세요. 기존 항목과 중복되면 알림도 중복될 수 있으니 활성화 전에 확인하세요.

현재 PC에서 업로드·설치·Notification 테스트를 실행하지 않았습니다. JSON 구문·개수·참조를 확인한 파일이며, 대상 PC에서 설치와 동작을 검증해야 합니다. 기존 실행 중인 탐지 정의와 알림 상태는 변경하지 않았습니다.

이 Pack에는 n8n Workflow, Agent 설정, Wazuh 룰, Graylog Input/Pipeline, Stream의 라우팅 규칙, 로그/이벤트 이력이 포함되지 않습니다. 기존 수집 구성이 있어야 탐지 조건이 실제 로그와 일치합니다.

## 비공개 원본

원본 API 응답은 프로젝트의 `backups/graylog/20261008_124730/`에 별도로 저장했습니다. 알림 URL과 인증 헤더가 포함될 수 있어 Git에서 제외했습니다. 이 내보내기는 MongoDB 전체 백업이 아니며 API가 감춘 암호화된 비밀까지 보존하지 않습니다.

## 다시 내보내기

게시판 프로젝트 루트의 PowerShell에서 실행하세요. 비밀번호는 표시하지 않고 입력받습니다.

```powershell
python .\scripts\export_graylog_alerts.py
```

다른 주소·사용자라면 `--url http://서버주소:9000/api --username 사용자명`을 추가하세요. 실행마다 새 시각 폴더를 만들며 이전 파일을 덮어쓰지 않습니다.

## 공식 근거

- [Graylog Content Packs](https://go2docs.graylog.org/current/what_more_can_graylog_do_for_me/content_packs.html): 화면에서 JSON으로 공유·설치하는 절차. 최신 문서이므로 6.1 화면과 명칭이 다를 수 있습니다.
- [Graylog 6.1 CatalogResource](https://github.com/Graylog2/graylog2-server/blob/6.1.0/graylog2-server/src/main/java/org/graylog2/rest/resources/system/contentpacks/CatalogResource.java): 의존성 해결 POST는 데이터를 변경하지 않는다고 명시합니다.
