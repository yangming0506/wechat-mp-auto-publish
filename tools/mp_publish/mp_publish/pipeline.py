from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mp_publish import deepseek, images, wechat


def validate_article_dict(data: dict[str, Any]) -> None:
    for k in ("title", "body_html", "cover_image_prompt", "inline_image_prompts"):
        if k not in data:
            raise ValueError(f"文章 JSON 缺少字段: {k}")
    if not isinstance(data["inline_image_prompts"], list):
        raise ValueError("inline_image_prompts 必须是数组")
    body = str(data["body_html"])
    ids = images.list_body_placeholders(body)
    n = len(data["inline_image_prompts"])
    if ids != list(range(n)):
        raise ValueError(
            f"占位符与 inline_image_prompts 不一致: 期望 <!--MP_IMG_0-->..<!--MP_IMG_{n-1}-->, 实际 {ids}"
        )


def run(
    topic: str,
    *,
    workdir: Path,
    dry_run_wechat: bool,
    no_inline_images: bool,
    cover_path: Path | None,
    max_inline: int,
    content_source_url: str,
) -> dict[str, Any]:
    if no_inline_images:
        max_inline = 0
    workdir.mkdir(parents=True, exist_ok=True)
    art_path = workdir / "article.json"
    raw = deepseek.generate_article(topic, max_inline=max_inline)
    validate_article_dict(raw)
    art_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    body = str(raw["body_html"])
    inline_prompts: list[str] = list(raw["inline_image_prompts"])
    if no_inline_images:
        if images.list_body_placeholders(body):
            raise RuntimeError("--no-inline-images 要求正文不含 <!--MP_IMG_n--> 占位符")
        inline_prompts = []

    cover_file = cover_path
    if cover_file is None:
        cb, _mime = images.generate_image_bytes(str(raw["cover_image_prompt"]))
        cover_file = workdir / "cover.jpg"
        cover_file.write_bytes(cb)

    inline_files: list[Path] = []
    for i, prompt in enumerate(inline_prompts):
        ib, _ = images.generate_image_bytes(prompt)
        p = workdir / f"inline_{i}.jpg"
        p.write_bytes(ib)
        inline_files.append(p)

    if dry_run_wechat:
        return {
            "ok": True,
            "dry_run_wechat": True,
            "article_json": str(art_path),
            "cover_image": str(cover_file),
            "inline_images": [str(p) for p in inline_files],
        }

    token = wechat.get_access_token()
    thumb_id = wechat.material_add_thumb(token, Path(cover_file))

    new_body = body
    for i, path in enumerate(inline_files):
        url = wechat.media_uploadimg(token, path)
        new_body = new_body.replace(f"<!--MP_IMG_{i}-->", f'<img src="{url}" />')

    media_id = wechat.draft_add_news(
        token,
        title=str(raw["title"]),
        author=str(raw.get("author") or ""),
        digest=str(raw.get("digest") or ""),
        content=new_body,
        thumb_media_id=thumb_id,
        content_source_url=content_source_url,
    )
    return {
        "ok": True,
        "article_json": str(art_path),
        "draft_media_id": media_id,
        "thumb_media_id": thumb_id,
    }


def run_from_json(
    article_json: Path,
    *,
    workdir: Path,
    dry_run_wechat: bool,
    no_inline_images: bool,
    cover_path: Path | None,
    content_source_url: str,
) -> dict[str, Any]:
    raw = json.loads(article_json.read_text(encoding="utf-8"))
    if no_inline_images:
        raw["inline_image_prompts"] = []
    validate_article_dict(raw)
    workdir.mkdir(parents=True, exist_ok=True)
    body = str(raw["body_html"])
    inline_prompts: list[str] = list(raw["inline_image_prompts"])
    if no_inline_images:
        if images.list_body_placeholders(body):
            raise RuntimeError("--no-inline-images 要求正文不含 <!--MP_IMG_n--> 占位符")

    cover_file = cover_path
    if cover_file is None:
        cb, _ = images.generate_image_bytes(str(raw["cover_image_prompt"]))
        cover_file = workdir / "cover.jpg"
        cover_file.write_bytes(cb)

    inline_files: list[Path] = []
    for i, prompt in enumerate(inline_prompts):
        ib, _ = images.generate_image_bytes(prompt)
        p = workdir / f"inline_{i}.jpg"
        p.write_bytes(ib)
        inline_files.append(p)

    if dry_run_wechat:
        return {
            "ok": True,
            "dry_run_wechat": True,
            "article_json": str(article_json.resolve()),
            "cover_image": str(cover_file),
            "inline_images": [str(p) for p in inline_files],
        }

    token = wechat.get_access_token()
    thumb_id = wechat.material_add_thumb(token, Path(cover_file))
    new_body = body
    for i, path in enumerate(inline_files):
        url = wechat.media_uploadimg(token, path)
        new_body = new_body.replace(f"<!--MP_IMG_{i}-->", f'<img src="{url}" />')

    media_id = wechat.draft_add_news(
        token,
        title=str(raw["title"]),
        author=str(raw.get("author") or ""),
        digest=str(raw.get("digest") or ""),
        content=new_body,
        thumb_media_id=thumb_id,
        content_source_url=content_source_url,
    )
    return {
        "ok": True,
        "article_json": str(article_json.resolve()),
        "draft_media_id": media_id,
        "thumb_media_id": thumb_id,
    }
