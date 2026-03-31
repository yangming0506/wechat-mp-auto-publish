from __future__ import annotations

import base64
import re
from typing import Any

import httpx

from mp_publish.config import (
    require_env,
    seedance_base,
    seedance_image_size,
    seedance_model,
)


def generate_image_bytes(prompt: str, *, timeout: float = 180.0) -> tuple[bytes, str]:
    base = seedance_base()
    if not base:
        raise RuntimeError(
            "未配置 SEEDANCE_API_BASE，无法生图。可改用 --cover-path + --no-inline-images 并自行提供正文无图 HTML。"
        )
    api_key = require_env("SEEDANCE_API_KEY")
    model = seedance_model()
    size = seedance_image_size()
    path = "/v1/images/generations"
    url = f"{base}{path}"
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "url",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        r = client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"图片 API HTTP {r.status_code}: {r.text[:500]}")
        data = r.json()
    item = _first_image_item(data)
    if "url" in item and item["url"]:
        img_url = item["url"]
        with httpx.Client(timeout=timeout, follow_redirects=True) as c2:
            ir = c2.get(img_url)
            ir.raise_for_status()
            return ir.content, _guess_mime(ir.headers.get("content-type"), img_url)
    b64 = item.get("b64_json") or item.get("base64")
    if b64:
        raw = base64.b64decode(b64)
        return raw, "image/png"
    raise RuntimeError(f"无法解析图片响应: {data!r}")


def _first_image_item(data: dict[str, Any]) -> dict[str, Any]:
    if "data" in data and data["data"]:
        return data["data"][0]
    if "images" in data and data["images"]:
        el = data["images"][0]
        if isinstance(el, dict):
            return el
        if isinstance(el, str):
            return {"url": el}
    if "image_url" in data:
        return {"url": data["image_url"]}
    raise RuntimeError(f"未知图片 JSON 结构: {list(data)[:10]}")


def _guess_mime(content_type: str | None, url: str) -> str:
    if content_type and content_type.startswith("image/"):
        return content_type.split(";")[0].strip()
    if re.search(r"\.jpe?g(\?|$)", url, re.I):
        return "image/jpeg"
    if re.search(r"\.png(\?|$)", url, re.I):
        return "image/png"
    if re.search(r"\.webp(\?|$)", url, re.I):
        return "image/webp"
    return "image/jpeg"


def list_body_placeholders(body_html: str) -> list[int]:
    ids = [int(m.group(1)) for m in re.finditer(r"<!--MP_IMG_(\d+)-->", body_html)]
    return sorted(set(ids))
