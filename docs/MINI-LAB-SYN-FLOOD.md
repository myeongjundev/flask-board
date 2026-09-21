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

WSL의 Kali라면 복사하지 않고 Windows 경로에서 바로 돌린다. `/mnt/c` 아래 파일은 실행
권한이 없을 수 있어 `bash`로 실행한다.

```bash
bash /mnt/c/SKTaleph/flask-board/scripts/syn_flood_lab.sh 192.168.3.14
```

**공격 사이에 5분 이상 간격을 둔다.** 이벤트 정의의 알림 유예가 5분이라, 그 안의 재공격은
이벤트만 쌓이고 알림은 가지 않는다(아래 5절).

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

## 5. Graylog·n8n 설정값 (DB에만 있으므로 여기 적어 둔다)

Graylog 이벤트 정의와 알림은 Graylog의 MongoDB에만 저장된다. 컨테이너를 새로 만들면
아래 값으로 다시 만든다.

### 이벤트 정의 `hping3 SYN flood 탐지 테스트`

| 항목 | 값 |
| --- | --- |
| 검색 | `rule:hping3-synflood` |
| 검색 범위 / 실행 주기 | 60초 / 15초 |
| 사용자 정의 필드 (Template, string) | `src_ip` = `${source.src_ip}` · `syn_count` = `${source.syn_count}` · `student` = `${source.student}` |
| 알림 유예 (Grace period) | 5분 — 15초마다 60초를 다시 검색해 한 메시지를 4번 잡으므로 |
| 알림 | `n8n webhook (login-guard)` |

### 알림 `n8n webhook (login-guard)` 본문

```json
{"student":"${event.fields.student}","source":"graylog","alerts":[{"ip":"${event.fields.src_ip}","level":10,"rule":"hping3-synflood","fail_count":"${event.fields.syn_count}"}]}
```

학생 식별자·출발지·SYN 개수를 본문에 글자로 적어 두지 않는다. 처음 판은 학생 식별자가
수업 자료 계정으로, 이후 판은 IP와 개수까지 고정값으로 적혀 있어 실제 공격 정보가 n8n에
가지 않았다.

권한 회수 쪽 이벤트 정의에도 같은 방식으로 `student` = `${source.student}` 필드를 두고,
알림 `n8n webhook(priv-guard)` 본문은 `"student": "${event.fields.student}"`를 쓴다.

### n8n `3-kali-hping-syn-flood-test`

- `거부인가?` IF: `{{ $json.decision }}` equals `deny` — 비교값 앞뒤에 공백이 없어야 한다
- `메세지 거부🚫` 문구 (SYN 경보일 때만 개수를 넣는다)

```text
🚫 [거부] {{ $json.src_ip }} — {{ $json.rule === 'hping3-synflood' ? 'SYN ' + Number($json.fail_count).toLocaleString('en-US') + '개 탐지 · ' + $json.rule + ' → ' + $json.decision : $json.reason }} · 심각도 {{ $json.severity }} (학생 {{ $json.student }})
```

n8n 2.x는 저장만으로는 운영 Webhook에 반영되지 않는다. 고친 뒤 **Publish**까지 누른다.
