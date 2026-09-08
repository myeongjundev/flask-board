# 심화 S2 · S3 — n8n에 붙여 넣을 것 (참고용)

> 두 항목 모두 n8n 캔버스 작업이다. 여기에는 **그대로 붙여 넣을 값**만 정리해 둔다.
> 가산점은 **최대 +6**이고 S1은 이미 되어 있으므로, S2·S3·S4 중 **하나만** 더 하면
> 상한에 닿는다. S4는 n8n을 건드리지 않으므로 워크플로 작업과 병행할 수 있다.
> (`docs/S4-SCHEDULER.md`)

---

## S2 — 허용은 슬랙 1곳, 거부는 3곳 전부

IF 노드가 이미 두 갈래를 만든다. 연결만 바꾸면 된다.

```text
IF (decision == "deny")
 ├─ true  ─┬─▶ 슬랙
 │         ├─▶ 디스코드
 │         └─▶ 텔레그램
 └─ false ──▶ 슬랙          ← 여기만 하나로
```

허용 갈래에서 디스코드·텔레그램으로 가는 연결을 지우면 끝이다. 두 갈래 모두
**게시판 저장 노드로는 계속 연결**되어야 한다 — D 항목은 허용·거부 둘 다 저장을
요구한다.

제출문에는 "왜 이렇게 나눴는지"를 한 줄 적으면 좋다. 예: *거부는 즉시 대응이 필요해
3곳 모두 알리고, 허용은 기록 성격이라 슬랙 한 곳만 남긴다.*

---

## S3 — 디스코드 embeds 카드 (거부 빨강 / 허용 초록)

디스코드 Webhook은 `content` 대신 `embeds` 배열을 받으면 카드로 그린다.
색은 **10진수 정수**여야 한다. 16진수를 그대로 넣으면 400이 난다.

| 판정 | 색 | 16진수 | 10진수 |
| --- | --- | --- | --- |
| deny | 빨강 | `#ED4245` | `15548997` |
| allow | 초록 | `#57F287` | `5763719` |

### 거부 갈래 — HTTP Request 노드 JSON 본문

```json
{
  "embeds": [
    {
      "title": "🚫 접근 거부",
      "color": 15548997,
      "description": "={{ $json.reason }}",
      "fields": [
        { "name": "출발지 IP", "value": "={{ $json.src_ip }}", "inline": true },
        { "name": "심각도",    "value": "={{ $json.severity }}", "inline": true },
        { "name": "실패 횟수", "value": "={{ $json.fail_count }}", "inline": true },
        { "name": "제출자",    "value": "={{ $json.student }}", "inline": false }
      ],
      "footer": { "text": "login_alert_lab" },
      "timestamp": "={{ $json.generated_at }}"
    }
  ]
}
```

### 허용 갈래

```json
{
  "embeds": [
    {
      "title": "✅ 접근 허용",
      "color": 5763719,
      "description": "={{ $json.src_ip }} · {{ $json.student }}",
      "footer": { "text": "login_alert_lab" },
      "timestamp": "={{ $json.generated_at }}"
    }
  ]
}
```

### 막히면 볼 곳

| 증상 | 원인 |
| --- | --- |
| 400 Bad Request | `color`에 `#` 또는 16진수를 넣었다. 10진수만 받는다 |
| 400 Bad Request | `fields[].value`가 빈 문자열이다. 디스코드는 빈 값을 거부한다 |
| `{{ }}`가 그대로 보임 | 입력칸이 표현식 모드가 아니다 |
| `timestamp` 오류 | ISO 8601이어야 한다. Code 노드의 `generated_at`이 `new Date().toISOString()`이라 그대로 맞는다 |

`fail_count`가 `0`일 수 있으므로, 빈 값 거부가 걱정되면 `"={{ $json.fail_count ?? 0 }}"`
처럼 기본값을 준다.

### 주의

Webhook 주소는 노드에 직접 쓰지 말고 **n8n Credential**에 넣는다. 캡처에도 주소가
찍히지 않게 한다 (E1은 위반 시 0점).
