"""애플리케이션 보안 이벤트를 Graylog GELF UDP 입력으로 전송한다."""
import json
import socket

from flask import current_app, request


def request_src_ip():
    """GELF src_ip 필드용 출발지. 랩 프록시가 넘긴 첫 IP를 우선한다."""
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.remote_addr or "0.0.0.0"


def send_gelf(short_message, rule, **fields):
    """GELF 전송 실패가 사용자 로그인 흐름을 막지 않도록 조용히 실패한다."""
    # 테스트가 실습 Graylog로 가짜 경보를 쏘지 않도록 설정으로 끌 수 있다.
    if not current_app.config.get("GELF_ENABLED", True):
        return False
    host = current_app.config.get("GELF_HOST", "localhost")
    port = int(current_app.config.get("GELF_PORT", 12201))
    message = {
        "version": "1.1",
        "host": "board",
        "short_message": short_message,
        "level": 4,
        "_rule": rule,
    }
    for key, value in fields.items():
        message[f"_{key}"] = value

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(json.dumps(message).encode("utf-8"), (host, port))
    except (OSError, TypeError, ValueError):
        # SIEM 장애가 인증 기능 장애로 번지면 안 된다.
        return False
    return True
