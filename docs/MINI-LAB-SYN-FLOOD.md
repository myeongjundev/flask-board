# 미니 실습 — SYN flood 탐지 자동화

허가된 로컬 실습망에서만 실행한다. 기본 공격 시간은 2초이며 스크립트가 자동으로
종료한다.

## 1. 사전 확인

- 게시판: `http://localhost:5000`
- Graylog: `http://localhost:9000`
- n8n: `http://localhost:5678`
- Docker: MySQL, Graylog, MongoDB, OpenSearch, n8n 실행 중
- Graylog GELF UDP 입력: `12201`
- Graylog 검색 규칙: `rule:hping3-synflood`
- n8n 운영 Webhook: `/webhook/login-guard`

## 2. Kali에서 실행

`scripts/syn_flood_lab.sh`를 Kali로 복사한 뒤 실행한다.

```bash
chmod +x syn_flood_lab.sh
sudo ./syn_flood_lab.sh 192.168.3.14
```

정상 출력 예시:

```text
탐지된 SYN(3초 창): 12345
[+] 임계값(1000) 초과 — Graylog GELF 경보 전송 완료
```

IP가 바뀌면 마지막 인자만 현재 Windows IPv4로 변경한다.

## 3. 확인 순서

1. Graylog 검색에서 `rule:hping3-synflood` 조회
2. Graylog `Alerts > Events`에서 이벤트 matched 확인
3. n8n `Executions`에서 `3-kali-hping-syn-flood-test` 성공 확인
4. Discord/Slack/Telegram 알림 확인
5. 게시판 `/dashboard`에서 `deny / High / src_ip` 이벤트 확인

Graylog 이벤트 정의는 15초마다 최근 60초를 검색하므로 메시지 수집 후 n8n 실행까지
최대 약 15초가 걸릴 수 있다.

## 4. 제출 캡처

1. 게시판 대시보드의 새 이벤트
2. Discord, Slack, Telegram 메시지
3. Graylog 검색 결과와 matched 이벤트
4. n8n 실행 성공 및 전체 흐름도
