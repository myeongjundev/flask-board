#!/usr/bin/env python3
"""허용목록 밖 관리자 계정을 찾아 신고하거나 일반 등급으로 회수한다.

기본 실행은 Graylog GELF 신고만 하며, ``--revoke``를 함께 주면 게시판의
관리자 API를 호출해 해당 계정을 일반(0) 등급으로 되돌린다.
"""
import argparse
import json
import os
import socket
import sys
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def load_env():
    """추가 패키지 없이 프로젝트의 .env를 읽는다."""
    path = BASE_DIR / ".env"
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def cfg():
    load_env()
    allowlist = [
        username.strip()
        for username in os.environ.get("ADMIN_ALLOWLIST", "").split(",")
        if username.strip()
    ]
    return {
        "board": os.environ.get("BOARD_URL", "http://localhost:5000").rstrip("/"),
        "key": os.environ.get("ADMIN_API_KEY", "")
        or os.environ.get("SECURITY_API_KEY", ""),
        "allowlist": allowlist,
        "gelf_host": os.environ.get(
            "GELF_HOST", os.environ.get("GRAYLOG_HOST", "localhost")
        ),
        "gelf_port": int(
            os.environ.get("GELF_PORT", os.environ.get("GRAYLOG_PORT", "12201"))
        ),
        "student": os.environ.get(
            "STUDENT_NAME", os.environ.get("STUDENT", "myeongjundev")
        ),
        "src_ip": os.environ.get("BOARD_SRC_IP", "127.0.0.1"),
    }


def get_json(url, key=None, method="GET", body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if key:
        request.add_header("X-API-Key", key)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def find_violations(config):
    """게시판에서 관리자 목록을 받아 허용목록 밖 계정만 반환한다."""
    result = get_json(
        f"{config['board']}/api/admin/users?role=admin", key=config["key"]
    )
    return [
        user
        for user in result.get("users", [])
        if user["username"] not in config["allowlist"]
    ]


def send_gelf(config, user):
    """관리자 권한 위반 한 건을 GELF UDP 메시지로 보낸다."""
    message = {
        "version": "1.1",
        "host": socket.gethostname(),
        "short_message": (
            f"privilege violation: '{user['username']}' has unauthorized admin"
        ),
        "level": 4,
        "_rule": "priv-unauthorized-admin",
        "_user": user["username"],
        "_granted_by": user.get("role_granted_by") or "unknown",
        "_src_ip": config["src_ip"],
        "_student": config["student"],
        "_count": 1,
    }
    payload = json.dumps(message).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.sendto(payload, (config["gelf_host"], config["gelf_port"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="신고 없이 위반만 출력")
    parser.add_argument(
        "--revoke", action="store_true", help="게시판 API로 직접 권한까지 회수"
    )
    args = parser.parse_args()
    config = cfg()

    if not config["key"]:
        print("[!] ADMIN_API_KEY(또는 SECURITY_API_KEY)가 비어 있습니다.")
        return 2

    try:
        violations = find_violations(config)
    except Exception as error:
        print(f"[!] 게시판 조회 실패: {error}")
        return 1

    if not violations:
        allowed = config["allowlist"] or "(비어 있음: 모든 관리자가 위반)"
        print(f"[OK] 과잉권한 위반 없음 (허용목록: {allowed})")
        return 0

    names = ", ".join(user["username"] for user in violations)
    print(f"[!] 과잉권한 관리자 {len(violations)}건 탐지: {names}")
    for user in violations:
        username = user["username"]
        if args.dry_run:
            print(f"    - {username} [dry-run]")
            continue

        send_gelf(config, user)
        print(f"    - {username} -> Graylog 신고(rule=priv-unauthorized-admin)")
        if args.revoke:
            result = get_json(
                f"{config['board']}/api/admin/revoke",
                key=config["key"],
                method="POST",
                body={
                    "username": username,
                    "student": config["student"],
                    "reason": f"봇 직접 회수: 허용목록 밖 관리자 ({username})",
                    "src_ip": config["src_ip"],
                    "source": "privilege-guard-bot",
                },
            )
            print(
                f"      회수: {result.get('old_role')}->{result.get('new_role')} "
                f"(event {result.get('event_id')})"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
