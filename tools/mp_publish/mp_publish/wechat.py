from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from mp_publish.config import default_token_cache_path, require_env


class WeChatError(RuntimeError):
    pass


def _wx_check(data: dict[str, Any]) -> None:
    if "errcode" in data and data["errcode"] not in (0, None):
        raise WeChatError(f"微信接口错误 {data.get('errcode')}: {data.get('errmsg')}")


def get_access_token(*, force_refresh: bool = False) -> str:
    appid = require_env("WECHAT_APP_ID")
    secret = require_env("WECHAT_APP_SECRET")
    cache_path = default_token_cache_path()
    now = time.time()
    if not force_refresh and cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            token = cached.get("access_token")
            exp = float(cached.get("expire_at", 0))
            if token and exp - 120 > now:
                return str(token)
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": appid, "secret": secret}
    with httpx.Client(timeout=30.0) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    _wx_check(data)
    token = data["access_token"]
    expires_in = int(data.get("expires_in", 7200))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"access_token": token, "expire_at": now + expires_in}, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )
    return str(token)


def media_uploadimg(access_token: str, image_path: Path, *, timeout: float = 60.0) -> str:
    url = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
    params = {"access_token": access_token}
    data_bytes = image_path.read_bytes()
    name = image_path.name or "image.jpg"
    mime = "image/jpeg"
    if name.lower().endswith(".png"):
        mime = "image/png"
    files = {"media": (name, data_bytes, mime)}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, params=params, files=files)
        r.raise_for_status()
        out = r.json()
    _wx_check(out)
    u = out.get("url")
    if not u:
        raise WeChatError(f"uploadimg 未返回 url: {out!r}")
    return str(u)


def material_add_thumb(access_token: str, image_path: Path, *, timeout: float = 120.0) -> str:
    url = "https://api.weixin.qq.com/cgi-bin/material/add_material"
    params = {"access_token": access_token, "type": "thumb"}
    data_bytes = image_path.read_bytes()
    name = image_path.name or "thumb.jpg"
    mime = "image/jpeg"
    if name.lower().endswith(".png"):
        mime = "image/png"
    files = {"media": (name, data_bytes, mime)}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, params=params, files=files)
        r.raise_for_status()
        out = r.json()
    _wx_check(out)
    mid = out.get("media_id")
    if not mid:
        raise WeChatError(f"add_material thumb 未返回 media_id: {out!r}")
    return str(mid)


def draft_add_news(
    access_token: str,
    *,
    title: str,
    author: str,
    digest: str,
    content: str,
    thumb_media_id: str,
    content_source_url: str = "",
    need_open_comment: int = 0,
    only_fans_can_comment: int = 0,
    timeout: float = 60.0,
) -> str:
    url = "https://api.weixin.qq.com/cgi-bin/draft/add"
    params = {"access_token": access_token}
    article: dict[str, Any] = {
        "article_type": "news",
        "title": title,
        "author": author or "",
        "digest": digest or "",
        "content": content,
        "thumb_media_id": thumb_media_id,
        "need_open_comment": need_open_comment,
        "only_fans_can_comment": only_fans_can_comment,
    }
    if content_source_url:
        article["content_source_url"] = content_source_url
    body = {"articles": [article]}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, params=params, json=body)
        r.raise_for_status()
        out = r.json()
    _wx_check(out)
    mid = out.get("media_id")
    if not mid:
        raise WeChatError(f"draft/add 未返回 media_id: {out!r}")
    return str(mid)
