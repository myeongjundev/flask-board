# n8n 로그인 경보 워크플로 구성

## 흐름

```text
Webhook → Code → IF(decision=deny)
                    ├─ deny 메시지 → 메신저들 ─┐
                    └─ allow 메시지 → 메신저들 ├→ 게시판 저장
```

두 갈래에서 게시판 저장 노드를 각각 연결해도 된다. 병합 노드를 쓴다면 두 입력의
모든 아이템이 통과하는지 실행 기록에서 확인한다.

## Code 노드

언어는 JavaScript를 사용하고 `Run Once for All Items`로 실행한다.

```javascript
const DENY_LEVEL = 10;
const input = $input.first().json;
const body = input.body ?? input;
const student = body.student;
const alerts = Array.isArray(body.alerts) ? body.alerts : [];

return alerts.map((alert) => {
  const level = Number(alert.level);
  const severity = level >= 10 ? 'High' : level >= 7 ? 'Medium' : 'Low';
  const decision = level >= DENY_LEVEL ? 'deny' : 'allow';
  return {
    json: {
      student,
      src_ip: alert.ip,
      level,
      rule: String(alert.rule ?? ''),
      fail_count: Number(alert.fail_count ?? 0),
      severity,
      decision,
      reason: `level ${level} (rule ${alert.rule ?? '-'}) → ${decision}`,
      source: 'login_alert_lab',
      generated_at: new Date().toISOString(),
    },
  };
});
```

확인할 것:

- 입력 경보 2건이 출력 아이템 2개가 됨
- 레벨 10은 `deny`·`High`
- 레벨 3은 `allow`·`Low`
- `DENY_LEVEL`만 바꾸면 판정 결과가 달라짐

## IF 노드

조건은 문자열 `{{$json.decision}}`이 `deny`와 같은지 비교한다.

- true: `🚫 [거부] {{$json.src_ip}} · {{$json.reason}} · {{$json.severity}} · {{$json.student}}`
- false: `✅ [허용] {{$json.src_ip}} · {{$json.student}}`

메시지를 만들 때 기존 JSON 필드를 제거하지 않는다. 게시판 저장 노드가 `src_ip`,
`decision`, `severity`, `reason`, `student`를 다시 사용한다.

## 게시판 저장 HTTP Request 노드

- Method: `POST`
- URL: `http://host.docker.internal:5000/api/security/events`
- Header: `X-API-Key` — n8n Credential에서 주입
- Body Content Type: JSON
- 응답 성공 기준: HTTP `201`과 `id`

JSON 본문에는 현재 아이템의 다음 필드를 보낸다.

```json
{
  "student": "={{$json.student}}",
  "src_ip": "={{$json.src_ip}}",
  "fail_count": "={{$json.fail_count}}",
  "decision": "={{$json.decision}}",
  "severity": "={{$json.severity}}",
  "reason": "={{$json.reason}}",
  "source": "={{$json.source}}",
  "generated_at": "={{$json.generated_at}}"
}
```

## 안전 확인

- 실제 Webhook URL, 메신저 토큰, 봇 토큰, API 키를 소스나 캡처에 노출하지 않음
- Export한 워크플로 JSON에서 토큰과 Credential 값을 다시 검색함
- 제출 증적에는 합성 IP와 본인 식별자만 사용함
- 외부 공개 서비스로 옮길 때는 조회 API와 `/dashboard`에도 로그인·소유권 검사를 추가함
