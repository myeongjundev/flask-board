# Wazuh 수업 환경

강사님 저장소의 2026-10-07 커밋 `341605a`에 있는 구성을
`docker-compose.yml`로 옮겼습니다. Wazuh 4.9.0 Manager·Indexer·Dashboard를
실행하고, 대시보드 접속 포트는 `443`입니다.

현재 PC의 Graylog와 기존 Wazuh Manager가 연결된 네트워크는
`9_graylog_default`이므로 강사님 코드의 `graylog_default`를 이 이름으로
맞췄습니다. 기존 Manager 전용 구성은 `docker-compose-manager-only.yml`에
보존했습니다. Manager 전용 파일은 변경 전 원본 참고용입니다.
설정 이전 후 운영에는 `docker-compose.yml`을 사용합니다.

## 설정 파일 위치

수업에서 생성한 파일은 게시판 루트의 `config/`에 있습니다.
`wazuh/docker-compose.yml`의 상대 경로는 `../config/`로 맞췄습니다.
인증서 생성 파일 `generate-indexer-certs.yml`도 게시판 루트에 있습니다.
다음 구조는 게시판 프로젝트 루트 기준입니다.

```text
config/
├─ wazuh_indexer_ssl_certs/
│  ├─ root-ca-manager.pem
│  ├─ root-ca.pem
│  ├─ wazuh.manager.pem
│  ├─ wazuh.manager-key.pem
│  ├─ wazuh.indexer.pem
│  ├─ wazuh.indexer-key.pem
│  ├─ admin.pem
│  ├─ admin-key.pem
│  ├─ wazuh.dashboard.pem
│  └─ wazuh.dashboard-key.pem
├─ wazuh_indexer/
│  ├─ wazuh.indexer.yml
│  └─ internal_users.yml
└─ wazuh_dashboard/
   ├─ opensearch_dashboards.yml
   └─ wazuh.yml
```

인증서와 설정은 Compose의 서비스 별칭(`wazuh.manager`, `wazuh.indexer`,
`wazuh.dashboard`) 및 계정 정보와 일치해야 합니다.
저장소의 계정 설정은 Wazuh 수업용 데모 값입니다. 개인 운영 계정의 비밀번호,
인증서 및 TLS 개인키는 커밋하지 않습니다. 각 PC에서 생성한 파일은 Git 제외 경로에 둡니다.

인증서가 없는 환경에서는 `config/certs.yml`의 노드 이름을 확인하고 다음 생성 명령을
실행합니다. 기존 인증서가 있는 환경에서는 다시 생성하지 않고 현재 연결에 사용 중인
인증서를 보존합니다.

```powershell
docker compose -f generate-indexer-certs.yml run --rm generator
```

이 명령은 인증서를 생성하며 Manager 설정·Agent 등록·외부 저장 볼륨을 복원하지는 않습니다.

## 기존 Manager 전환 준비

이전 Manager는 `/var/ossec/logs`만 볼륨에 저장했습니다.
수업에서 생성한 `backup/wazuh_etc_20261008_101911.tar.gz`는 빈 볼륨의 백업이므로
복원용으로 사용하지 않습니다.

실제 Manager 설정은 `backups/wazuh-manager/migration_*/`에 Linux 소유권과
권한을 보존한 tar.gz로 백업합니다. Agent 키, 사용자 규칙·디코더·공유 설정,
API 설정, Agent DB와 Filebeat registry를 포함합니다. Agent DB는 SQLite
무결성 검사를 수행합니다. 대용량 취약점 피드 캐시는 별도로 새 queue 볼륨에
직접 복사하므로 이 tar.gz 백업에는 포함되지 않습니다.

새 Compose에는 Wazuh 4.9.0 공식 구성의 저장 볼륨을 추가했습니다.
`wazuh_etc`, `wazuh_api_configuration`, `wazuh_queue`, `wazuh_var_multigroups`,
사용자 스크립트 경로와 Filebeat registry를 유지합니다. 기존 `wazuh_logs`
볼륨은 계속 사용합니다.
이전한 볼륨은 `external: true`로 지정해 Compose가 재생성하거나 삭제하지
않도록 했습니다. 다른 PC에서는 기존 볼륨을 복원한 뒤 이 구성을 실행합니다.

실행 중인 Manager의 설정 파일을 별도로 복사하는 예:

```powershell
New-Item -ItemType Directory -Force backups/wazuh-manager
docker cp wazuh-manager:/var/ossec/etc backups/wazuh-manager/etc
```

## 실행과 확인

기존 Manager 설정 이전을 마친 뒤, 게시판 프로젝트 루트에서 실행합니다.

```powershell
docker network inspect 9_graylog_default
docker compose -f wazuh/docker-compose.yml config --quiet
docker compose -f wazuh/docker-compose.yml up -d
docker compose -f wazuh/docker-compose.yml ps
docker exec wazuh-manager /var/ossec/bin/agent_control -l
docker exec wazuh-manager /var/ossec/bin/agent_groups -s -i 001
docker exec wazuh-manager filebeat test output -c /etc/filebeat/filebeat.yml
docker compose -f wazuh/docker-compose.yml logs --tail 100
```

대시보드 주소: `https://localhost/`

`config --quiet`는 Compose 구문 검증이며 인증서 존재나 서비스 기동을
보장하지 않습니다. Flask의 `/dashboard`와 Wazuh Dashboard는 별도 화면입니다.
현재 `board-host`의 ID는 `001`이고 `default, flask-board` 그룹을 사용합니다.
수업 자료의 `002` 대신 `001`로 검색합니다. 기존 그룹 설정은
`C:\SKT aleph\flask-board\logs\security.log` 수집 및 `templates` 실시간
감시를 포함합니다. FIM 경보는 `100220`, `100221`, `100222` 규칙으로 확인합니다.

실제 TLS 개인키와 Agent 키가 포함된 백업은 `.gitignore`로 제외합니다.
수업 자료: https://app.notion.com/p/wazuh_4-9_-d730741730ea82ed95b881c8f214105f
볼륨 구성 참고: https://github.com/wazuh/wazuh-docker/blob/v4.9.0/single-node/docker-compose.yml

## 2026-10-08 기동 검증

Manager·Indexer·Dashboard 모두 실행 중이며 `9_graylog_default`에 연결됩니다.
`board-host`(001)는 Active입니다. Filebeat의 TLS 검증 및 Indexer 연결 테스트가
`talk to server... OK`로 통과했고, Indexer에서 Agent 001 경보와 테스트 FIM
규칙 100220 경보가 조회됐습니다. 생성·수정·삭제 테스트 파일은 삭제했습니다.
Dashboard는 443 포트에서 실행됩니다.

읽기 전용 점검 스크립트와 개인별 진단 절차:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_wazuh.ps1 -AgentId 001
```

다른 PC의 Agent ID는 명령 출력에서 확인한 실제 값을 사용합니다. 스크립트 종료 코드만으로
전체 정상 여부를 판단하지 않고 각 단계의 출력과 실제 경보를 확인합니다.
[LLM 검증 길라잡이](../docs/WAZUH-LLM-VERIFICATION-GUIDE.md)와
[Graylog Alerts 설정 기록](../graylog/exports/README.md)을 함께 참고하세요.
