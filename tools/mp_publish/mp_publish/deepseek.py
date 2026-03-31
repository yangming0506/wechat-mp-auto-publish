from __future__ import annotations

import json
import re
from typing import Any

import httpx

from mp_publish.config import deepseek_base, deepseek_model, require_env

SYSTEM = """你是微信公众号图文编辑。请仅输出一个 JSON 对象（不要 Markdown 围栏），字段如下：
- title: 标题，<=32 字
- author: 作者，<=16 字，可为空字符串
- digest: 摘要，<=120 字
- cover_image_prompt: 封面图英文或中文描述，横版构图、适合 2.35:1 安全区
- body_html: 正文 HTML，仅使用 p、h2、h3、ul、ol、li、strong、em、blockquote；不要用 script、iframe、外部链接图片
- inline_image_prompts: 数组，与正文中占位符一一对应

正文必须插入占位符 <!--MP_IMG_0-->、<!--MP_IMG_1-->... 按顺序出现，数量等于 inline_image_prompts 长度（建议 0~3 张）。
不要输出 Unicode 转义形式的汉字，直接使用正常 UTF-8 字符。"""


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        text = m.group(0)
    return json.loads(text)


def generate_article(topic: str, *, max_inline: int = 3, timeout: float = 120.0) -> dict[str, Any]:
    api_key = require_env("DEEPSEEK_API_KEY")
    base = deepseek_base()
    model = deepseek_model()
    if max_inline <= 0:
        user = f"写作主题：{topic}\n内文不要插入任何 <!--MP_IMG_n-->，inline_image_prompts 必须为空数组 []。"
    else:
        user = (
            f"写作主题：{topic}\n"
            f"内文插图占位符最多 {max_inline} 个（可更少）。"
        )
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        "temperature": 0.6,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{base}/v1/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"DeepSeek 响应异常: {data!r}") from e
    return _parse_json_object(content)
