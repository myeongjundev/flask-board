# Graylog Event Definitions — 실제 설정 기록

내보낸 시각: 2026-10-08T12:47:30+09:00 / Graylog 6.1.16+4a05695

Event Definitions 11개와 Notifications 6개를 실행 중인 API에서 읽었습니다. 제목과 설명의 오타도 실제 설정대로 보존했습니다. 아래 조건은 제목에서 추정한 값이 아니라 API 값입니다.

## 목록

| 제목 | 검색 조건 | 집계 / 임계값 | 그룹 | 검색 범위 / 실행 간격 | 상태 / 우선순위 | 연결 알림 |
| --- | --- | --- | --- | --- | --- | --- |
| 10 - Suricata IDS 경보 폭주 탐지(src_ip, 5회 이상) | rule:ids-alert | (count(*) >= 5) | src_ip | 30초 / 30초 | ENABLED / 2 | 3-n8n Webhook(ip-block) |
| 3-IP 반복 로그인 실패 탐지 (src_ipp, 5회이상) | rule:login-bruteforce | (count(*) >= 5) | src_ip | 120초 / 15초 | ENABLED / 2 | 3-n8n Webhook(ip-block) |
| 4- 계정 스프레이 탐지 (한 IP 가 서로 다른 계정으로 접근 5번 이상) | rule:login-bruteforce | (card(username) > 4) | src_ip | 120초 / 15초 | ENABLED / 2 | 4-n8n Webhook(security-alert) |
| 5-복합 공격 상관 탐지 (같은 IP: 네트워크 + 앱 동시) | rule:login-bruteforce OR rule:portscan | (card(rule) > 1) | src_ip | 120초 / 15초 | ENABLED / 3 | 4-n8n Webhook(security-alert) |
| 6-인시던트 승격 - 잠긴 계정에서 지속 시도 (같은 출발지 ip 3회 이상) | rule:login-bruteforce AND locked:1 | (count(*) > 2) | src_ip | 60초 / 60초 | ENABLED / 3 | 5-n8n Webhook (incident) |
| 7-Wazuh  브루트포스 탐지 (rule 100211) | wazuh_rule_id:100211 | 일치 메시지별 이벤트(집계 없음) | 없음 | 60초 / 60초 | ENABLED / 2 | 6 - n8n Webhook (wazuh-alert) |
| 8- Wazuh 웹 파일 위변조 웰쉡 탐지 (rule 100220, 100221, 100222) | wazuh_rule_id:(100220 OR 100221 OR 100222) | 일치 메시지별 이벤트(집계 없음) | 없음 | 15초 / 15초 | ENABLED / 3 | 6 - n8n Webhook (wazuh-alert) |
| 9-웹 스캐너 404 폭주 탐지 (src_ip, 30회 초과) | rule:web-scan | (count(*) > 30) | src_ip | 30초 / 30초 | ENABLED / 2 | 3-n8n Webhook(ip-block) |
| System notification events | 시스템 내부 이벤트 | 해당 없음 | 없음 | 해당 없음 / 해당 없음 | ENABLED / 1 | 없음 |
| hping3 SYN flood 탐지 테스트 | rule:hping3-synflood  | 일치 메시지별 이벤트(집계 없음) | 없음 | 60초 / 15초 | ENABLED / 2 | n8n webhook (login-guard) |
| 자동 회수봇 테스트 | rule:priv-unauthorized-admin | 일치 메시지별 이벤트(집계 없음) | 없음 | 1초 / 1초 | ENABLED / 2 | n8n Webhook(priv-guard) |

## 정의별 상세 값

### 10 - Suricata IDS 경보 폭주 탐지(src_ip, 5회 이상)

- 원본 ID: `6ac5d5b2a9bc4432b34dae8f`
- 설명: Suricata IDS 가 탐지한 공격(nmap 포트 스캔, sqlmap SQLi)을 src_ip 별 집계 -> n8n 차단
- 검색 Stream ID: `[]` (빈 배열은 전체 검색)
- Event Key: `["src_ip"]`
- 알림 유예 시간: 120초
- Backlog: 0개
- 마지막 일치(원본 UTC): `2026-10-07T05:29:04.078Z`

Custom Fields:

```json
{
  "src_ip": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.src_ip}",
        "require_values": false
      }
    ]
  },
  "username": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.username}",
        "require_values": false
      }
    ]
  }
}
```

### 3-IP 반복 로그인 실패 탐지 (src_ipp, 5회이상)

- 원본 ID: `6ab1e61680130f5bcf77dd64`
- 설명: 같은 출발지 IP 에서 2분 내 로그인 실패 5회 이상 -> n8n 으로 실 차단 트리거
- 검색 Stream ID: `[]` (빈 배열은 전체 검색)
- Event Key: `["src_ip"]`
- 알림 유예 시간: 60초
- Backlog: 0개
- 마지막 일치(원본 UTC): `2026-10-08T03:11:31.246Z`

Custom Fields:

```json
{
  "src_ip": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.src_ip}",
        "require_values": false
      }
    ]
  },
  "username": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.username}",
        "require_values": false
      }
    ]
  }
}
```

### 4- 계정 스프레이 탐지 (한 IP 가 서로 다른 계정으로 접근 5번 이상)

- 원본 ID: `6ab33377871b930097ad6a63`
- 설명: 같은 src_ip 에서 서로 다른 username 5개이상 로그인 실패 -> 패스워드/계정 스프레이 의심.
- 검색 Stream ID: `[]` (빈 배열은 전체 검색)
- Event Key: `["src_ip"]`
- 알림 유예 시간: 120초
- Backlog: 0개
- 마지막 일치(원본 UTC): `2026-09-23T03:40:50.818Z`

Custom Fields:

```json
{
  "src_ip": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.src_ip}",
        "require_values": false
      }
    ]
  },
  "username": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.username}",
        "require_values": false
      }
    ]
  }
}
```

### 5-복합 공격 상관 탐지 (같은 IP: 네트워크 + 앱 동시)

- 원본 ID: `6ab33671871b930097ad734f`
- 설명: 같은 src_ip에서 서로 다른 rule 2종 이상(예: portscan+login-bruteforce)-> 네트워크, 앱 계층 복합 공격 의심(고위험)
- 검색 Stream ID: `[]` (빈 배열은 전체 검색)
- Event Key: `["src_ip"]`
- 알림 유예 시간: 120초
- Backlog: 0개
- 마지막 일치(원본 UTC): `2026-09-23T03:42:26.260Z`

Custom Fields:

```json
{
  "rule": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.rule}",
        "require_values": false
      }
    ]
  },
  "src_ip": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.src_ip}",
        "require_values": false
      }
    ]
  },
  "username": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.username}",
        "require_values": false
      }
    ]
  }
}
```

### 6-인시던트 승격 - 잠긴 계정에서 지속 시도 (같은 출발지 ip 3회 이상)

- 원본 ID: `6ab9d3899fa0120467b91a61`
- 설명: 대응(계정잠금)이 끝난 뒤에도 같은 출발지에서 잠긴 계정 로그인 시도가 이어지면 사건으로 승격해 인시던트 티켓을 만든다. 탐지 대응 다음 단계인 기록, 추적
- 검색 Stream ID: `[]` (빈 배열은 전체 검색)
- Event Key: `["src_ip"]`
- 알림 유예 시간: 120초
- Backlog: 0개
- 마지막 일치(원본 UTC): `2026-09-28T07:08:09.176Z`

Custom Fields:

```json
{
  "src_ip": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.src_ip}",
        "require_values": false
      }
    ]
  },
  "rule": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.rule}",
        "require_values": false
      }
    ]
  },
  "username": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.username}",
        "require_values": false
      }
    ]
  }
}
```

### 7-Wazuh  브루트포스 탐지 (rule 100211)

- 원본 ID: `6abf0e162b6c892d6d2d0f4b`
- 설명: wazuh 에이전트가 게시판 보안 로그에서 동일 IP 다수 로그인 실패를 탐지
- 검색 Stream ID: `["6abc77811cf9ab654f385bac"]` (빈 배열은 전체 검색)
- Event Key: `["srcip"]`
- 알림 유예 시간: 120초
- Backlog: 0개
- 마지막 일치(원본 UTC): `2026-10-08T03:09:50.131Z`

Custom Fields:

```json
{
  "agent": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_agent_name}",
        "require_values": false
      }
    ]
  },
  "description": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_rule_description}",
        "require_values": false
      }
    ]
  },
  "rule_id": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_rule_id}",
        "require_values": false
      }
    ]
  },
  "rule_level": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_rule_level}",
        "require_values": false
      }
    ]
  },
  "srcip": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_data_srcip}",
        "require_values": false
      }
    ]
  },
  "user": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_data_dstuser}",
        "require_values": false
      }
    ]
  }
}
```

### 8- Wazuh 웹 파일 위변조 웰쉡 탐지 (rule 100220, 100221, 100222)

- 원본 ID: `6abf164e2b6c892d6d2d283d`
- 설명: Wazuh FIM 이 게시판 templates 폴더의 파일 추가, 변경 , 삭제 를 탐지
- 검색 Stream ID: `["6abc77811cf9ab654f385bac"]` (빈 배열은 전체 검색)
- Event Key: `["rule_id", "file"]`
- 알림 유예 시간: 60초
- Backlog: 0개
- 마지막 일치(원본 UTC): `2026-10-08T02:53:55.016Z`

Custom Fields:

```json
{
  "agent": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_agent_name}",
        "require_values": false
      }
    ]
  },
  "description": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_rule_description}",
        "require_values": false
      }
    ]
  },
  "file": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_file}",
        "require_values": false
      }
    ]
  },
  "fim_event": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_syscheck_event}",
        "require_values": false
      }
    ]
  },
  "rule_id": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_rule_id}",
        "require_values": false
      }
    ]
  },
  "rule_level": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.wazuh_rule_level}",
        "require_values": false
      }
    ]
  }
}
```

### 9-웹 스캐너 404 폭주 탐지 (src_ip, 30회 초과)

- 원본 ID: `6ac485f5dcf1f53a046f94bb`
- 설명: 단일 src_ip 가 60초 내 404를 30회 이상 유발 (nikto, gobuster 등 웹스캔) -> n8n 차단
- 검색 Stream ID: `[]` (빈 배열은 전체 검색)
- Event Key: `["src_ip"]`
- 알림 유예 시간: 120초
- Backlog: 0개
- 마지막 일치(원본 UTC): `2026-10-06T06:14:35.923Z`

Custom Fields:

```json
{
  "src_ip": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.src_ip}",
        "require_values": false
      }
    ]
  },
  "username": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.username}",
        "require_values": false
      }
    ]
  }
}
```

### System notification events

- 원본 ID: `6aa89dd20f3a7c17107c8c30`
- 설명: Reserved event definition for system notification events
- 검색 Stream ID: `[]` (빈 배열은 전체 검색)
- Event Key: `[]`
- 알림 유예 시간: 0초
- Backlog: 0개
- 마지막 일치(원본 UTC): `2026-09-30T04:42:18.261Z`

Custom Fields:

```json
{}
```

### hping3 SYN flood 탐지 테스트

- 원본 ID: `6ab099104e5fe51ab3e9618d`
- 설명: rule:hping3-synflood 로그 수신시 n8n 통보
- 검색 Stream ID: `[]` (빈 배열은 전체 검색)
- Event Key: `[]`
- 알림 유예 시간: 0초
- Backlog: 1개
- 마지막 일치(원본 UTC): `2026-09-22T04:59:50.972Z`

Custom Fields:

```json
{}
```

### 자동 회수봇 테스트

- 원본 ID: `6aa8c10a3860df77831ac7ec`
- 설명: bot을 이용한 n8n으로 admin의 이상권한 회수. 봇으로 권한 자동회수
- 검색 Stream ID: `[]` (빈 배열은 전체 검색)
- Event Key: `[]`
- 알림 유예 시간: 1초
- Backlog: 1개
- 마지막 일치(원본 UTC): `2026-09-17T03:06:09.936Z`

Custom Fields:

```json
{
  "granted_by": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.granted_by}",
        "require_values": false
      }
    ]
  },
  "src_ip": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.src_ip}",
        "require_values": false
      }
    ]
  },
  "user": {
    "data_type": "string",
    "providers": [
      {
        "type": "template-v1",
        "template": "${source.user}",
        "require_values": false
      }
    ]
  }
}
```

## LLM 검토 요청문

```text
이 MD와 event-definitions.review.json, notifications.review.json은 실제 Graylog API 내보내기입니다.
1. 제목·설명과 실제 query, group_by, series, conditions가 일치하는지 확인해 주세요.
2. 검색 범위, 실행 간격, grace_period_ms, Custom Fields 및 연결 Notification을 비교해 주세요.
3. 내 PC의 실제 로그 필드와 샘플 메시지로 조건을 검증해 주세요. 설정 파일만으로 실행 성공을 단정하지 마세요.
4. Wazuh 100211, 100220/100221/100222 탐지와 Graylog 웹훅 연동을 별도로 확인해 주세요.
5. 원본 ID를 내 PC에 그대로 적용하지 말고 내 Stream과 Notification ID를 확인해 주세요.
6. 사실, 추정, 추가 증거가 필요한 항목을 구분하고 변경 전후 결과를 기록해 주세요.
7. 공유본의 인증 정보와 URL은 제거되었으므로 실제 Notification 설정에서 따로 검증해 주세요.
```

실제 조건 전체는 함께 저장된 JSON을 기준으로 확인하세요. 이 MD는 설정 기록이며 실행 검증 보고서가 아닙니다.
