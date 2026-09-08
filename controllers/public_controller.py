"""기존 부산 테마여행 화면과 공공데이터 호출."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, render_template

public_bp = Blueprint("public", __name__)


def fetch_busan_travel(content_id=None):
    service_key = current_app.config.get("PUBLIC_API_KEY", "")
    if not service_key:
        raise RuntimeError("PUBLIC_API_KEY 환경변수에 공공데이터 인증키를 설정해주세요.")
    if "%" in service_key:
        service_key = unquote(service_key)
    query = urlencode({
        "serviceKey": service_key,
        "numOfRows": 100,
        "pageNo": 1,
        "resultType": "json",
        **({"UC_SEQ": content_id} if content_id else {}),
    })
    api_request = Request(
        f"{current_app.config['PUBLIC_API_URL']}?{query}",
        headers={"User-Agent": "flask-board-busan-travel-practice/1.0"},
    )
    try:
        with urlopen(api_request, timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"공공데이터 API 호출에 실패했습니다: {exc}") from exc

    api_result = payload.get("getRecommendedKr") or payload.get("response", {})
    header = api_result.get("header", {})
    result_code = header.get("code", header.get("resultCode", "00"))
    if str(result_code) != "00":
        message = header.get("message", header.get("resultMsg", "알 수 없는 API 오류"))
        raise RuntimeError(f"공공데이터 API 오류: {message}")
    items = api_result.get("item")
    if items is None:
        items = api_result.get("body", {}).get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if not isinstance(items, list):
        return []
    for item in items:
        for field in ("MAIN_IMG_NORMAL", "MAIN_IMG_THUMB"):
            url = item.get(field)
            if url and url.startswith("/"):
                item[field] = f"https://www.visitbusan.net{url}"
    return items


@public_bp.get("/public-post")
@public_bp.get("/public-posts")
@public_bp.get("/busan-travel")
def busan_travel_list():
    try:
        travels, error = fetch_busan_travel(), None
    except RuntimeError as exc:
        travels, error = [], str(exc)
    return render_template("busan_travel_list.html", travels=travels, error=error)


@public_bp.get("/public-post/<content_id>")
@public_bp.get("/public-posts/<content_id>")
@public_bp.get("/busan-travel/<content_id>")
def busan_travel_detail(content_id):
    try:
        travels = fetch_busan_travel(content_id)
        travel = next(
            (item for item in travels if str(item.get("UC_SEQ")) == content_id),
            travels[0] if travels else None,
        )
        error = None if travel else "해당 테마여행 정보를 찾을 수 없습니다."
    except RuntimeError as exc:
        travel, error = None, str(exc)
    return render_template(
        "busan_travel_detail.html", travel=travel,
        content_id=content_id, error=error,
    )
