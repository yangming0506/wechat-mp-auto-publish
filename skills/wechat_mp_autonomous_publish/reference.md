# 参考：API 形态与示例（需对照最新官方文档）

## Python CLI（`tools/mp_publish`）

```bash
cd tools/mp_publish
pip install -r requirements.txt

export DEEPSEEK_API_KEY=...
export SEEDANCE_API_KEY=...
export SEEDANCE_API_BASE=https://你的网关根地址   # 需支持 POST {base}/v1/images/generations
export SEEDANCE_IMAGE_MODEL=你的模型名
export WECHAT_APP_ID=...
export WECHAT_APP_SECRET=...

python3 -m mp_publish run --topic "春季养生科普"
python3 -m mp_publish run --topic "..." --dry-run-wechat
python3 -m mp_publish from-json --article ./out/mp_publish/article.json
python3 -m mp_publish refresh-token
```

生图接口默认按 **OpenAI Images** 形态解析响应（`data[0].url` 或 `b64_json`）。若你的 Seedance/火山方舟使用不同 JSON 字段，请改 `mp_publish/images.py` 中 `_first_image_item` 或包一层兼容网关。

## DeepSeek（Chat Completions）

- 文档：<https://api-docs.deepseek.com/>
- 示例请求（curl 思路）：`POST {base}/v1/chat/completions`，`Authorization: Bearer $DEEPSEEK_API_KEY`，`Content-Type: application/json`，body 含 `model`、`messages`。
- 建议在 `messages` 中要求 **仅输出 JSON** 或 fenced JSON，便于后续解析；解析失败时让模型自我修复一轮。

## Seedance / Seedream 图片

- 火山引擎方舟等产品线文档会列出 **文生图** endpoint、模型 ID、请求体（prompt、size、response_format 等）。用户若使用第三方兼容网关，以网关文档为准。
- 通用模式：`POST` 生图 → 得到 url 或 b64 → `curl -o cover.jpg` → 再调微信 `media/upload` 等接口。

## 微信草稿与发布

- 总览：<https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Overview.html>
- 草稿箱：<https://developers.weixin.qq.com/doc/offiaccount/Draft_Box/Getting_Draft_Box_List.html>
- 实现前务必在文档中核对：**路径**、**必填字段**、`media_id` / `thumb_media_id` 的获取方式是否与本项目成文时一致。

## IP 白名单与本机 OpenClaw / 家用宽带

公众平台里配置的 **IP 白名单**，校验的是：**你发起请求访问 `api.weixin.qq.com` 时，微信看到的源站公网 IP**（出站流量的出口 IP）。与 OpenClaw 装在本地还是云上无关，只与「最终是谁的机器在直连微信」有关。

| 做法 | 说明 |
|------|------|
| **白名单本机出口 IP** | 浏览器搜「IP」或 `curl ifconfig.me` 看当前公网 IP，加到公众平台后台。家用宽带若 **动态拨号**，IP 会变，需在变更后 **重新改白名单**（或办理运营商 **固定公网 IP** / 企业宽带）。 |
| **白名单一台云上小机的固定 IP（推荐自动化）** | 在阿里云/腾讯云等买 **轻量或 ECS + 弹性公网 IP**，只把 **该 EIP** 写入白名单。OpenClaw 仍可在自家电脑上用，但 **实际调微信接口** 放在云上：`ssh` 在远端跑 `python3 -m mp_publish …`，或本机调一个 **仅内网/鉴权可用的 HTTP 触发服务**，由云端再调微信。这样白名单 **长期稳定**。 |
| **全程走固定出口代理/VPN** | 只有当代理出口是 **固定且可预期** 的 IP 时才适用；常见民用 VPN 出口多变或与他人共用，**不适合** 写进白名单。 |
| **确认是否必须** | 以公众平台当前设置为准：部分能力或测试号策略可能不同；后台若强制白名单则必须满足其一。 |

**要点**：OpenClaw 在本地只影响「谁在下指令」；解决白名单要么 **固定你直连微信的那条链路的公网 IP**，要么 **把直连微信的那一跳固定到一台已备案的白名单服务器上**。

## openclaw.json 注入示例（片段）

```json5
{
  skills: {
    entries: {
      wechat_mp_autonomous_publish: {
        enabled: true,
        apiKey: { source: "env", provider: "default", id: "DEEPSEEK_API_KEY" },
        env: {
          SEEDANCE_API_KEY: "从安全处读取",
          SEEDANCE_API_BASE: "https://网关根地址",
          SEEDANCE_IMAGE_MODEL: "服务商要求的模型名",
          WECHAT_APP_ID: "...",
          WECHAT_APP_SECRET: "...",
        },
      },
    },
  },
}
```

勿将真实密钥写入仓库；生产环境优先系统密钥管理或 `SecretRef`。
