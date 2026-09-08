# 심화 S4 — 작업 스케줄러로 5분마다 자동 실행

> 문제지 심화 항목: *윈도우 작업 스케줄러로 `alert_sender.py`를 5분마다 자동 실행* (+3)
>
> n8n을 건드리지 않는 항목이라 워크플로 작업과 독립적으로 진행할 수 있다.

## 준비된 것

| 파일 | 역할 |
| --- | --- |
| `scripts/run_alert_sender.ps1` | 스케줄러가 부르는 래퍼. 경로·인코딩·로그를 처리한다 |
| `scripts/register_alert_task.ps1` | 스케줄러 항목을 등록한다. 확인 후 등록 |
| `scripts/unregister_alert_task.ps1` | 등록한 항목을 지운다. 빈 폴더까지 정리 |
| `logs/alert_sender.log` | 실행 기록. **이 파일이 S4의 증적이다** (`.gitignore`로 제외됨) |

## 등록되는 이름

```text
폴더    \SKT-ALEPH-TEMP\
작업명  TEMP-alert-sender-5min-DELETE-AFTER-SUBMIT
```

제출이 끝나면 지워야 하는 임시 작업이라, 작업 스케줄러 목록에서 한눈에 찾히고
이름만으로 용도와 처분 시점이 읽히게 두었다. 전용 폴더에 넣었으므로 정리할 때
폴더째 사라진다. 설명란에도 무엇인지와 삭제 방법을 적어 두었다.

## 왜 파이썬을 직접 부르지 않고 래퍼를 두는가

세 가지가 스케줄러에서만 깨진다.

**1. 시작 위치** — 스케줄러는 작업 디렉터리를 보장하지 않는다. `alert_sender.py`는
같은 폴더의 `.env`를 읽으므로, 위치가 어긋나면 `CONFIG_MISSING`으로 끝난다. 래퍼가
저장소 폴더로 먼저 이동한다.

**2. PATH** — 로그인 셸의 PATH와 스케줄러 세션의 PATH가 다르다. `python`이 안 잡힐
수 있어 등록 시점의 전체 경로를 `ALERT_SENDER_PYTHON`에 저장해 둔다.

**3. 한글 출력** — 콘솔 기본 인코딩이 cp949라 그냥 두면 한글 오류 메시지에서
`UnicodeEncodeError`가 난다. 래퍼가 `PYTHONUTF8=1`을 켠다.

> 만드는 과정에서 네 번째가 하나 더 나왔다. 파이썬을 `&`로 직접 부르고 `2>&1`로
> 스트림을 합치면, Windows PowerShell 5.1은 stderr 한 줄 한 줄을 오류 레코드로
> 감싼다. `$ErrorActionPreference='Stop'`과 만나면 스크립트가 그 자리에서 끝나고
> **로그를 남기는 줄에 도달하지 못한다.** 그래서 `Start-Process`로 띄우고 두 스트림을
> 파일로 받는다.

## 등록

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_alert_task.ps1
```

무엇이 등록되는지 보여준 뒤 `y`를 받아야 진행한다. 등록되는 내용:

- `\SKT-ALEPH-TEMP\TEMP-alert-sender-5min-DELETE-AFTER-SUBMIT`
- 1분 뒤 시작, 이후 **5분마다** 무기한 반복
- 배터리에서도 실행, 실행 시간 상한 5분
- 창을 띄우지 않음

## 확인

```powershell
$t = @{ TaskPath = '\SKT-ALEPH-TEMP\'; TaskName = 'TEMP-alert-sender-5min-DELETE-AFTER-SUBMIT' }
Start-ScheduledTask @t
Get-ScheduledTaskInfo @t | Select-Object LastRunTime, LastTaskResult, NextRunTime
Get-Content logs\alert_sender.log -Tail 20
```

`LastTaskResult`가 `0`이면 전송까지 성공한 것이다.

## 로그 읽는 법

각 실행이 한 줄로 요약되고 그 아래에 출력이 들여쓰기로 붙는다.

| 표시 | 종료코드 | 뜻 |
| --- | --- | --- |
| `OK` | 0 | n8n이 200으로 받았다 |
| `SEND_FAILED` | 1 | n8n에 못 보냈다. 꺼져 있거나 Webhook 주소가 다르다 |
| `CONFIG_MISSING` | 2 | `.env`의 `N8N_WEBHOOK_URL`·`STUDENT_NAME`이 비어 있다 |
| `NO_PYTHON` | 3 | 스케줄러 세션에서 python을 못 찾았다 |

## 실제 기록 (2026-09-08)

등록 직후의 로그다. Webhook이 아직 404이던 구간과, 워크플로가 Active로 켜진 뒤
성공한 구간이 한 파일에 함께 남았다.

```text
[2026-09-08 11:51:18] SEND_FAILED (exit=1)   수동 실행, Webhook 404
[2026-09-08 12:01:35] SEND_FAILED (exit=1)   스케줄러
[2026-09-08 12:02:22] SEND_FAILED (exit=1)   스케줄러 — 5분 주기 확인
[2026-09-08 12:06:01] OK (exit=0)            Webhook 연결 후 성공
```

이 한 파일이 두 가지를 동시에 보인다.

- **A3** — n8n에 못 보내도 프로그램이 죽지 않고 오류를 남기고 끝난다
- **S4** — 사람이 부르지 않아도 5분마다 실행된다

`webhook-test/...`는 캔버스에서 **Listen 중일 때만** 살아 있는 임시 주소다. 스케줄러가
쓰는 주소는 워크플로를 Active로 켠 뒤의 `webhook/...`이어야 한다. `SEND_FAILED`가
계속 쌓이면 `.env`의 `N8N_WEBHOOK_URL`이 그 production 주소인지 먼저 본다.

## 증적으로 남길 것

| 캡처 | 무엇을 보이나 |
| --- | --- |
| `images/13-task-scheduler.png` | 작업 스케줄러 `SKT-ALEPH-TEMP` 폴더에 작업이 있고 트리거가 "5분마다" |
| `images/14-task-log.png` | `logs\alert_sender.log`에 **서로 다른 시각의 `OK` 항목이 2개 이상** |

한 번만 찍힌 로그는 "등록했다"만 보이고 "돌고 있다"를 못 보인다. **5분 이상 두었다가**
`OK`가 두 줄 이상 쌓인 뒤에 찍는다.

## 되돌리기

```powershell
powershell -ExecutionPolicy Bypass -File scripts\unregister_alert_task.ps1
```

제출 뒤에는 **반드시** 지운다. 그대로 두면 5분마다 계속 n8n으로 요청이 간다.

이 스크립트는 작업을 지우고, 비어 있으면 `\SKT-ALEPH-TEMP` 폴더도 정리하고, 등록 때
만든 사용자 환경변수 `ALERT_SENDER_PYTHON`도 되돌린다. **로그는 증적이므로 남긴다.**
