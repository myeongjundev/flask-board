"""합성 로그인 경보 두 건을 n8n Webhook으로 전송한다."""
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "").strip()
STUDENT_NAME = os.environ.get("STUDENT_NAME", "").strip()
TIMEOUT_SECONDS = 10
ALERTS = [
    {"ip": "1.2.3.114", "level": 10, "rule": "5712", "fail_count": 20},
    {"ip": "192.168.0.10", "level": 3, "rule": "1001", "fail_count": 1},
]


def build_payload():
    return {"student": STUDENT_NAME, "alerts": ALERTS}


def main():
    if not N8N_WEBHOOK_URL or not STUDENT_NAME:
        print("N8N_WEBHOOK_URL과 STUDENT_NAME을 .env에 설정하세요.", file=sys.stderr)
        return 2
    payload = build_payload()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        error_type = type(exc).__name__
        print(
            f"[n8n] 전송 실패 ({error_type}): n8n 연결과 워크플로 상태를 확인하세요.",
            file=sys.stderr,
        )
        return 1
    print(f"[n8n] POST -> {response.status_code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
