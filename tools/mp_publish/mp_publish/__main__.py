from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mp_publish import pipeline, wechat


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="微信公众号：DeepSeek 撰文 + Seedance 生图 + 草稿箱 draft/add")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--workdir",
        type=Path,
        default=Path("out/mp_publish"),
        help="中间产物目录（article.json、封面与插图）",
    )
    common.add_argument(
        "--dry-run-wechat",
        action="store_true",
        help="只生成 article.json 与图片，不调微信接口",
    )
    common.add_argument(
        "--no-inline-images",
        action="store_true",
        help="不要正文插图；topic 模式会指示模型不生成占位符",
    )
    common.add_argument(
        "--cover-path",
        type=Path,
        default=None,
        help="使用本地封面图，跳过封面文生图",
    )
    common.add_argument(
        "--content-source-url",
        default="",
        help="阅读原文链接（可选）",
    )

    r = sub.add_parser("run", parents=[common], help="按主题全流程")
    r.add_argument("--topic", required=True, help="文章主题 / 写作指令")
    r.add_argument("--max-inline", type=int, default=3, help="正文插图占位符上限（0~6）")

    j = sub.add_parser("from-json", parents=[common], help="从已有 article.json 继续生图并发草稿")
    j.add_argument("--article", type=Path, required=True, help="article.json 路径")

    t = sub.add_parser("refresh-token", help="拉取 access_token 并写入缓存（排障用）")
    t.add_argument("--force", action="store_true", help="忽略缓存强制刷新")

    args = p.parse_args(argv)

    try:
        if args.cmd == "refresh-token":
            tok = wechat.get_access_token(force_refresh=args.force)
            print(json.dumps({"access_token": tok[:8] + "...", "ok": True}, ensure_ascii=False))
            return 0

        if args.cmd == "run":
            out = pipeline.run(
                args.topic,
                workdir=args.workdir,
                dry_run_wechat=args.dry_run_wechat,
                no_inline_images=args.no_inline_images,
                cover_path=args.cover_path,
                max_inline=max(0, min(6, args.max_inline)),
                content_source_url=args.content_source_url,
            )
        else:
            out = pipeline.run_from_json(
                args.article,
                workdir=args.workdir,
                dry_run_wechat=args.dry_run_wechat,
                no_inline_images=args.no_inline_images,
                cover_path=args.cover_path,
                content_source_url=args.content_source_url,
            )
    except (wechat.WeChatError, RuntimeError, ValueError) as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
