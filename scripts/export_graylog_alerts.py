"""Export Graylog alert configuration without installing or changing any entities.

Uses only the Python standard library. The catalog POST resolves dependencies;
it does not create a content pack on the server.
"""

import argparse
import base64
import copy
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid


ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = re.compile(
    r"password|secret|token|authorization|cookie|api[_-]?key|credential", re.I
)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scrub(value):
    """Review JSON only; keep conditions and templates except literal credentials."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SENSITIVE.search(key) else scrub(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        # Preserve ${...} template references; remove credential-like literals.
        return re.sub(
            r'(?i)("[^"\n]*(?:password|secret|token|api[_-]?key|authorization)[^"\n]*"\s*:\s*")([^"\n]*)(")',
            lambda match: match.group(0) if "${" in match[2] else match[1] + "[REDACTED]" + match[3],
            value,
        )
    return value


def unwrap(value):
    return value.get("@value") if isinstance(value, dict) and "@value" in value else value


def condition_text(expr, series):
    if not expr:
        return "해당 없음"
    kind = expr.get("expr")
    if kind == "number-ref":
        item = next((item for item in series if item["id"] == expr["ref"]), {})
        field = item.get("field") or "*"
        return f"{item.get('type', expr['ref'])}({field})"
    if kind == "number":
        value = expr["value"]
        return str(int(value)) if float(value).is_integer() else str(value)
    if "left" in expr and "right" in expr:
        return f"({condition_text(expr['left'], series)} {kind} {condition_text(expr['right'], series)})"
    return json.dumps(expr, ensure_ascii=False)


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_markdown(definitions, notifications, system, when):
    lookup = {item["id"]: item for item in notifications}
    lines = [
        "# Graylog Event Definitions — 실제 설정 기록",
        "",
        f"내보낸 시각: {when.isoformat(timespec='seconds')} / Graylog {system['version']}",
        "",
        f"Event Definitions {len(definitions)}개와 Notifications {len(notifications)}개를 실행 중인 API에서 읽었습니다. "
        "제목과 설명의 오타도 실제 설정대로 보존했습니다. 아래 조건은 제목에서 추정한 값이 아니라 API 값입니다.",
        "",
        "## 목록",
        "",
        "| 제목 | 검색 조건 | 집계 / 임계값 | 그룹 | 검색 범위 / 실행 간격 | 상태 / 우선순위 | 연결 알림 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for definition in definitions:
        config = definition["config"]
        condition = condition_text(config.get("conditions", {}).get("expression"), config.get("series", []))
        if config.get("type") == "aggregation-v1" and not config.get("series"):
            condition = "일치 메시지별 이벤트(집계 없음)"
        linked = [lookup.get(item["notification_id"], {}).get("title", item["notification_id"]) for item in definition["notifications"]]
        timings = " / ".join(
            f"{config[key] / 1000:g}초" if config.get(key) is not None else "해당 없음"
            for key in ("search_within_ms", "execute_every_ms")
        )
        values = (
            definition["title"], config.get("query") or "시스템 내부 이벤트", condition,
            ", ".join(config.get("group_by", [])) or "없음", timings,
            f"{definition.get('state', '미확인')} / {definition['priority']}", ", ".join(linked) or "없음",
        )
        lines.append("| " + " | ".join(cell(value) for value in values) + " |")
    lines += ["", "## 정의별 상세 값", ""]
    for definition in definitions:
        lines += [
            f"### {definition['title']}", "",
            f"- 원본 ID: `{definition['id']}`",
            f"- 설명: {definition.get('description') or '없음'}",
            f"- 검색 Stream ID: `{json.dumps(definition['config'].get('streams', []))}` (빈 배열은 전체 검색)",
            f"- Event Key: `{json.dumps(definition.get('key_spec', []), ensure_ascii=False)}`",
            f"- 알림 유예 시간: {definition['notification_settings'].get('grace_period_ms', 0) / 1000:g}초",
            f"- Backlog: {definition['notification_settings'].get('backlog_size', 0)}개",
            f"- 마지막 일치(원본 UTC): `{definition.get('matched_at') or '없음'}`",
            "", "Custom Fields:", "", "```json",
            json.dumps(scrub(definition.get("field_spec", {})), ensure_ascii=False, indent=2), "```", "",
        ]
    lines += [
        "## LLM 검토 요청문", "", "```text",
        "이 MD와 event-definitions.review.json, notifications.review.json은 실제 Graylog API 내보내기입니다.",
        "1. 제목·설명과 실제 query, group_by, series, conditions가 일치하는지 확인해 주세요.",
        "2. 검색 범위, 실행 간격, grace_period_ms, Custom Fields 및 연결 Notification을 비교해 주세요.",
        "3. 내 PC의 실제 로그 필드와 샘플 메시지로 조건을 검증해 주세요. 설정 파일만으로 실행 성공을 단정하지 마세요.",
        "4. Wazuh 100211, 100220/100221/100222 탐지와 Graylog 웹훅 연동을 별도로 확인해 주세요.",
        "5. 원본 ID를 내 PC에 그대로 적용하지 말고 내 Stream과 Notification ID를 확인해 주세요.",
        "6. 사실, 추정, 추가 증거가 필요한 항목을 구분하고 변경 전후 결과를 기록해 주세요.",
        "7. 공유본의 인증 정보와 URL은 제거되었으므로 실제 Notification 설정에서 따로 검증해 주세요.",
        "```", "",
        "실제 조건 전체는 함께 저장된 JSON을 기준으로 확인하세요. 이 MD는 설정 기록이며 실행 검증 보고서가 아닙니다.", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:9000/api")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password-stdin", action="store_true", help="Read one password line from stdin")
    args = parser.parse_args()
    password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else getpass.getpass("Graylog password: ")
    encoded = base64.b64encode(f"{args.username}:{password}".encode()).decode()

    def api(path, body=None):
        headers = {"Authorization": f"Basic {encoded}", "Accept": "application/json", "X-Requested-By": "graylog-file-export"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        request = Request(args.url.rstrip("/") + path, data=data, headers=headers)
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    def all_pages(path, key):
        items = []
        page = 1
        while True:
            response = api(f"{path}?page={page}&per_page=100")
            batch = response[key]
            items.extend(batch)
            if len(items) >= response["total"]:
                return items
            if not batch:
                raise RuntimeError(f"Incomplete pagination: {path}")
            page += 1

    system = api("/system")
    definitions = all_pages("/events/definitions", "event_definitions")
    notifications = all_pages("/events/notifications", "notifications")
    definition_ids = {item["id"] for item in definitions if item["config"]["type"] != "system-notifications-v1"}
    catalog = api("/system/catalog")["entities"]
    selected = [{"id": item["id"], "type": item["type"]} for item in catalog if item["id"] in definition_ids]
    if {item["id"] for item in selected} != definition_ids:
        raise RuntimeError("Not all custom definitions are exportable in the catalog")
    resolved = api("/system/catalog", {"entities": selected})
    exported_definitions = [item for item in resolved["entities"] if item["type"]["name"] == "event_definition"]
    if len(exported_definitions) != len(definition_ids):
        raise RuntimeError("Catalog export definition count mismatch")

    now = datetime.now().astimezone()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    private = ROOT / "backups" / "graylog" / stamp
    shared = ROOT / "graylog" / "exports" / stamp
    private.mkdir(parents=True, exist_ok=False)
    shared.mkdir(parents=True, exist_ok=False)
    write_json(private / "event-definitions.json", definitions)
    write_json(private / "notifications.json", notifications)
    write_json(private / "catalog-resolved.json", resolved)

    safe_notifications = scrub(notifications)
    for item in safe_notifications:
        item["config"]["url"] = "[개인 PC의 Webhook URL]"
        item["config"]["headers"] = "[개인 PC에서 다시 입력할 헤더]"
        item["config"]["basic_auth"] = "[개인 PC에서 다시 입력할 인증 정보]"
    write_json(shared / "event-definitions.review.json", scrub(definitions))
    write_json(shared / "notifications.review.json", safe_notifications)

    pack = {
        "v": "1", "id": str(uuid.uuid4()), "rev": 1,
        "name": "ALEPH Graylog Alert Definitions " + stamp,
        "summary": "개인별 검토를 위한 탐지 정의와 연결 알림",
        "description": "실제 Catalog 내보내기. 설치 후 개인 URL·인증·Stream 확인을 위해 모든 탐지 정의는 비활성 상태입니다.",
        "vendor": "flask-board lab", "url": "https://github.com/myeongjundev/flask-board",
        "created_at": now.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "server_version": system["version"], "parameters": [], "entities": copy.deepcopy(resolved["entities"]),
    }
    notification_number = 0
    for entity in pack["entities"]:
        if entity["type"]["name"] == "event_definition":
            entity["data"]["is_scheduled"] = {"@type": "boolean", "@value": False}
        if entity["type"]["name"] == "notification":
            notification_number += 1
            config = entity["data"]["config"]
            title = unwrap(entity["data"]["title"])
            for field in ("url", "headers", "body_template"):
                if field not in config:
                    continue
                original = unwrap(config[field])
                # URL and headers are always local. A body template containing
                # credential-like literal values must also be supplied locally.
                if field == "body_template" and scrub(original) == original and "Encrypted value was replaced" not in (original or ""):
                    continue
                parameter = f"notification_{notification_number}_{field}"
                config[field] = {"@type": "parameter", "@value": parameter}
                pack["parameters"].append({
                    "type": "string", "name": parameter, "title": f"{title} / {field}",
                    "description": "대상 PC에서 입력하세요. 원본 값은 공유 파일에 저장하지 않습니다.",
                    **({"default_value": "{}"} if field == "headers" else {}),
                })
            for field in list(config):
                if SENSITIVE.search(field):
                    del config[field]
    write_json(shared / "graylog-alerts.content-pack.json", pack)
    (shared / "EVENT-DEFINITIONS.md").write_text(build_markdown(definitions, notifications, system, now), encoding="utf-8")
    stream_titles = [unwrap(item["data"]["title"]) for item in pack["entities"] if item["type"]["name"] == "stream_title"]
    readme = f"""# Graylog Alerts 내보내기

생성: {now.isoformat(timespec='seconds')} / Graylog {system['version']}

## 파일

- `EVENT-DEFINITIONS.md`: 실제 검색·집계 조건과 LLM 검토 요청문.
- `event-definitions.review.json`: 시스템 기본 항목을 포함한 정의 {len(definitions)}개의 API 설정. 다른 PC에 직접 업로드하는 형식은 아닙니다.
- `notifications.review.json`: 알림 {len(notifications)}개의 검토용 설정. URL·인증 헤더·인증 정보는 제거했습니다.
- `graylog-alerts.content-pack.json`: 사용자 정의 {len(exported_definitions)}개와 연결 Notification {notification_number}개, 필요한 의존성을 Catalog API로 내보낸 Content Pack입니다. 시스템 기본 정의는 대상 서버의 기본 항목을 사용합니다.

## 다른 PC에서 가져오기

1. 우선 대상 PC의 기존 설정을 내보내 기록하세요. Graylog 버전은 원본({system['version']})의 제약 조건을 만족해야 합니다.
2. 대상 Graylog의 `System > Content Packs`에서 `Upload`로 Content Pack JSON을 선택하세요. 업로드와 설치는 별도 단계입니다.
3. 설치 전에 필요한 Stream 이름을 확인하세요: {', '.join(stream_titles) or '없음'}. `stream_title`은 기존 Stream을 이름으로 참조하며 Stream 규칙을 새로 만드는 항목이 아닙니다.
4. `Install` 단계에서 Notification별 URL 파라미터에 **대상 PC의 실제 n8n Webhook URL**을 입력하세요. Docker 안에서 호스트의 n8n을 호출한다면 `localhost`가 아닌 실제 도달 가능한 주소를 사용하세요.
5. headers 파라미터의 기본값 `{{}}`에는 인증이 없습니다. 필요한 인증 헤더를 대상 PC에서 입력하고, 설치 후 Notifications의 Basic Auth / API Secret도 직접 확인하세요. 암호화된 비밀은 API/Content Pack으로 완전히 복원할 수 없습니다.
6. 이 공유 Pack의 Event Definitions는 모두 **비활성 상태**입니다. 원본의 ENABLED/DISABLED 상태는 검토 JSON에 보존되어 있습니다. 검색 Stream, Custom Fields, Notification 연결을 확인한 뒤 필요한 정의만 활성화하세요.
7. 실제 로그로 탐지 이벤트 생성 → Notification 호출 → n8n 실행을 각각 검증하세요. 기존 항목과 중복되면 알림도 중복될 수 있으니 활성화 전에 확인하세요.

현재 PC에서 업로드·설치·Notification 테스트를 실행하지 않았습니다. JSON 구문·개수·참조를 확인한 파일이며, 대상 PC에서 설치와 동작을 검증해야 합니다. 기존 실행 중인 탐지 정의와 알림 상태는 변경하지 않았습니다.

이 Pack에는 n8n Workflow, Agent 설정, Wazuh 룰, Graylog Input/Pipeline, Stream의 라우팅 규칙, 로그/이벤트 이력이 포함되지 않습니다. 기존 수집 구성이 있어야 탐지 조건이 실제 로그와 일치합니다.

## 비공개 원본

원본 API 응답은 프로젝트의 `backups/graylog/{stamp}/`에 별도로 저장했습니다. 알림 URL과 인증 헤더가 포함될 수 있어 Git에서 제외했습니다. 이 내보내기는 MongoDB 전체 백업이 아니며 API가 감춘 암호화된 비밀까지 보존하지 않습니다.

## 다시 내보내기

게시판 프로젝트 루트의 PowerShell에서 실행하세요. 비밀번호는 표시하지 않고 입력받습니다.

```powershell
python .\\scripts\\export_graylog_alerts.py
```

다른 주소·사용자라면 `--url http://서버주소:9000/api --username 사용자명`을 추가하세요. 실행마다 새 시각 폴더를 만들며 이전 파일을 덮어쓰지 않습니다.

## 공식 근거

- [Graylog Content Packs](https://go2docs.graylog.org/current/what_more_can_graylog_do_for_me/content_packs.html): 화면에서 JSON으로 공유·설치하는 절차. 최신 문서이므로 6.1 화면과 명칭이 다를 수 있습니다.
- [Graylog 6.1 CatalogResource](https://github.com/Graylog2/graylog2-server/blob/6.1.0/graylog2-server/src/main/java/org/graylog2/rest/resources/system/contentpacks/CatalogResource.java): 의존성 해결 POST는 데이터를 변경하지 않는다고 명시합니다.
"""
    (shared / "README.md").write_text(readme, encoding="utf-8")
    manifest = {
        "exported_at": now.isoformat(), "graylog_version": system["version"],
        "definition_count": len(definitions), "custom_definition_count": len(exported_definitions),
        "notification_count": len(notifications), "content_pack_entity_count": len(pack["entities"]),
        "files": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for folder in (shared, private) for path in sorted(folder.iterdir())},
    }
    write_json(private / "manifest.json", manifest)
    print(json.dumps({"shared_folder": str(shared), "private_folder": str(private),
                      "definitions": len(definitions), "notifications": len(notifications),
                      "pack_definitions": len(exported_definitions)}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        print(f"Graylog API error: HTTP {error.code}; export incomplete", file=sys.stderr)
        sys.exit(1)
