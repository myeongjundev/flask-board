#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-192.168.3.14}"
N8N_HOST="${N8N_HOST:-$HOST}"
STUDENT="${STUDENT_NAME:-myeongjundev}"
PORTS=(5000 5678 9000 12201 3306)

echo "[+] 대상: $HOST"

open_ports=()
for port in "${PORTS[@]}"; do
  if hping3 -S -p "$port" -c 1 "$HOST" 2>&1 | grep -q "flags=SA"; then
    open_ports+=("$port")
  fi
done

open_json=$(IFS=,; echo "${open_ports[*]}")
payload=$(printf '{"host":"%s","open":[%s],"student":"%s"}' \
  "$HOST" "$open_json" "$STUDENT")

curl --fail-with-body --silent --show-error \
  --request POST "http://${N8N_HOST}:5678/webhook/vuln-scan" \
  --header "Content-Type: application/json" \
  --data "$payload"
echo
