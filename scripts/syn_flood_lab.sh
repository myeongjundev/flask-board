#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-192.168.3.14}"
PORT="${PORT:-5000}"
WINDOW_SECONDS="${WINDOW_SECONDS:-3}"
ATTACK_SECONDS="${ATTACK_SECONDS:-2}"
THRESHOLD="${THRESHOLD:-1000}"
STUDENT="${STUDENT_NAME:-myeongjundev}"
GRAYLOG_HOST="${GRAYLOG_HOST:-$TARGET}"
GRAYLOG_PORT="${GRAYLOG_PORT:-12201}"

if [[ $EUID -ne 0 ]]; then
  echo "root 권한이 필요합니다: sudo $0 $TARGET" >&2
  exit 2
fi
for command in hping3 tcpdump python3 timeout; do
  command -v "$command" >/dev/null || {
    echo "필수 명령이 없습니다: $command" >&2
    exit 3
  }
done

SOURCE_IP=$(ip route get "$TARGET" | awk '{for (i=1; i<=NF; i++) if ($i=="src") {print $(i+1); exit}}')
CAPTURE_FILE=$(mktemp)
trap 'rm -f "$CAPTURE_FILE"' EXIT

echo "[+] 대상: $TARGET:$PORT"
echo "[+] ${ATTACK_SECONDS}초 SYN 실습 시작"

timeout "$WINDOW_SECONDS" tcpdump -nn -l -i any \
  "dst host $TARGET and tcp dst port $PORT and tcp[tcpflags] & tcp-syn != 0" \
  >"$CAPTURE_FILE" 2>/dev/null &
CAPTURE_PID=$!
sleep 0.3
timeout "$ATTACK_SECONDS" hping3 --flood -S -p "$PORT" "$TARGET" \
  >/dev/null 2>&1 || true
wait "$CAPTURE_PID" || true

SYN_COUNT=$(grep -c 'Flags \[S\]' "$CAPTURE_FILE" || true)
echo "탐지된 SYN(${WINDOW_SECONDS}초 창): $SYN_COUNT"

if (( SYN_COUNT < THRESHOLD )); then
  echo "[-] 임계값($THRESHOLD) 미만 — Graylog 경보를 보내지 않습니다."
  exit 0
fi

python3 - "$GRAYLOG_HOST" "$GRAYLOG_PORT" "$SOURCE_IP" "$SYN_COUNT" "$STUDENT" <<'PY'
import json
import socket
import sys
import time

host, port, source_ip, syn_count, student = sys.argv[1:]
message = {
    "version": "1.1",
    "host": "kali-syn-lab",
    "short_message": f"hping3 SYN flood detected: {syn_count} SYN packets",
    "timestamp": time.time(),
    "level": 4,
    "_rule": "hping3-synflood",
    "_src_ip": source_ip,
    "_syn_count": int(syn_count),
    "_student": student,
    "_decision": "deny",
    "_severity": "High",
    "_source": "graylog",
}
payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(payload, (host, int(port)))
sock.close()
PY

echo "[+] 임계값($THRESHOLD) 초과 — Graylog GELF 경보 전송 완료"
