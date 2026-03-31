from __future__ import annotations

import os
from pathlib import Path


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    return v


def require_env(name: str) -> str:
    v = env(name)
    if not v:
        raise RuntimeError(f"缺少环境变量: {name}")
    return v


def default_token_cache_path() -> Path:
    p = env("WECHAT_TOKEN_CACHE")
    if p:
        return Path(p).expanduser()
    return Path.home() / ".cache" / "mp_publish" / "wechat_token.json"


def deepseek_base() -> str:
    return env("DEEPSEEK_API_BASE", "https://api.deepseek.com").rstrip("/")


def deepseek_model() -> str:
    return env("DEEPSEEK_MODEL", "deepseek-chat") or "deepseek-chat"


def seedance_base() -> str | None:
    b = env("SEEDANCE_API_BASE")
    if not b:
        return None
    return b.rstrip("/")


def seedance_model() -> str:
    return env("SEEDANCE_IMAGE_MODEL", "dall-e-3") or "dall-e-3"


def seedance_image_size() -> str:
    return env("SEEDANCE_IMAGE_SIZE", "1024x1024") or "1024x1024"
