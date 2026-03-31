---
name: wechat_mp_autonomous_publish
description: >-
  Autonomously publishes WeChat Official Account (微信公众号) articles: generates
  HTML copy with DeepSeek API, cover and inline images with Seedance/Seedream
  image APIs, then uploads media and uses draft/publish WeChat Open Platform
  endpoints. Use for OpenClaw 自主发文、DeepSeek 生成正文、Seedance 配图、公众号
  草稿发布 automation, or when the user references this skill name.
metadata: {"openclaw":{"requires":{"env":["DEEPSEEK_API_KEY","SEEDANCE_API_KEY","WECHAT_APP_ID","WECHAT_APP_SECRET"],"bins":["python3"]},"primaryEnv":"DEEPSEEK_API_KEY"}}
---

# 微信公众号自主发布（DeepSeek + Seedance）

在 **已认证服务号**、已开开发者模式且 IP 白名单（若需要）就绪的前提下，指导 Agent **端到端**完成：主题 → 正文生成 → 配图生成 → 微信上传 → 草稿 → 发布（或仅草稿）。具体接口字段以 [微信公众平台文档](https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Overview.html) 与 [DeepSeek](https://api-docs.deepseek.com/) / 所用 Seedance·Seedream 平台当前文档为准。

## 优先：用 Python 脚本跑全流程（省 OpenClaw / 模型 token）

仓库内已实现 CLI：**`tools/mp_publish/`**。Agent 应 **直接执行命令**，不要在对话里展开长 JSON 或手写 curl。

1. 安装依赖：`cd tools/mp_publish && pip install -r requirements.txt`（或 `make install`）。
2. 配置环境变量（与下文「环境变量」一致）；图片接口需 **`SEEDANCE_API_BASE`**（OpenAI 兼容 `/v1/images/generations` 的网关基址）及 **`SEEDANCE_IMAGE_MODEL`** 等。
3. 一键草稿：`python3 -m mp_publish run --topic "文章主题或写作说明"`  
   - 仅本地预览、不调微信：`--dry-run-wechat`  
   - 不要正文插图：`--no-inline-images`  
   - 指定本地封面、不生封面图：`--cover-path /path/to/cover.jpg`  
4. 成功时 stdout 打印 JSON，含 `draft_media_id`（草稿箱标识）；失败时 stderr 打印 `{"ok":false,"error":"..."}`。

脚本职责：DeepSeek 生成结构化 `article.json`（含 `<!--MP_IMG_n-->` 占位）→ Seedance 生图 → `uploadimg` 换图链 → 永久素材封面上传 → `draft/add`。详见 [reference.md](reference.md) 中的命令说明。

### 其它省 token 的做法（可选）

| 方式 | 说明 |
|------|------|
| **本 CLI + Makefile** | `TOPIC='...' make run`（见 `tools/mp_publish/Makefile`） |
| **CI 定时** | GitHub Actions / Cron 调用同一 CLI，密钥放仓库 Secrets |
| **两步人工** | `--dry-run-wechat` 产出 `article.json` 与图片，人在后台微调后再 `from-json` |
| **缩短 SKILL** | 对话里只触发 skill + 贴主题，由 Agent 调脚本，不重复贴接口文档 |

## 安全与合规（强制）

- 禁止在仓库、日志、对话中硬编码 `AppSecret`、长期 `access_token`、各平台 API Key。
- 正文中不得自动生成违法、侵权、医疗/金融等需资质承诺的内容；敏感行业先提示用户人工法务审核。
- 自动化**群发/发布**前必须让用户确认标题、摘要、外链、原创声明等等同后台选项。

## 环境变量（约定名）

| 变量 | 用途 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek 开放平台密钥 |
| `SEEDANCE_API_KEY` | Seedance 或兼容服务商提供的图片生成密钥（若走火山方舟，可与控制台 API Key 一致并仍用此名注入） |
| `WECHAT_APP_ID` / `WECHAT_APP_SECRET` | 微信公众平台应用身份 |

可选：`DEEPSEEK_API_BASE`（默认 `https://api.deepseek.com`）、图片侧 `SEEDANCE_API_BASE`、`SEEDANCE_IMAGE_MODEL`（具体值见用户服务商文档）。

OpenClaw 侧可将多密钥写入 `~/.openclaw/openclaw.json` 的 `skills.entries.wechat_mp_autonomous_publish.env`。

## 自主执行清单（推荐给 Agent 复用）

```
- [ ] 1. 确认发稿意图：主题、受众、是否要正文插图、是否只出本地预览
- [ ] 2. 在仓库执行：cd tools/mp_publish && pip install -r requirements.txt（首次）
- [ ] 3. python3 -m mp_publish run --topic "…"（可加 --dry-run-wechat / --no-inline-images / --cover-path）
- [ ] 4. 解析 stdout 的 JSON：dry_run 时检查 article.json 与图片；否则记录 draft_media_id，提醒用户到公众平台草稿箱核对
- [ ] 5. 正式发布前须用户确认；脚本当前只负责 draft/add，群发/发布由人在后台或后续接发布接口
```

（若 **不能** 跑 CLI，再按下方「步骤 A/B/C」手工调 API。）

## 步骤 A：用 DeepSeek 生成文章

1. 使用 **OpenAI 兼容** Chat Completions：`{base}/v1/chat/completions`（默认 base `https://api.deepseek.com`）。
2. 模型优先 `deepseek-chat`；长文可结合 `deepseek-reasoner` 做大纲再收敛正文（注意成本与延迟）。
3. 在 system/user 中要求输出 **可被程序解析** 的结构，再由 Agent 拼接为公众号 HTML，例如要求模型输出 JSON：

```json
{
  "title": "",
  "author": "",
  "digest": "",
  "sections": [{ "heading": "", "body_markdown": "" }]
}
```

4. 将 `sections` 转为公众号允许的 HTML（段落 `<p>`、小标题 `<h2>/<h3>`、列表等，避免脚本与非法外链），配图位置预留占位，稍后替换为已上传图片 URL。

5. 控制生文长度与摘要：`digest` 通常需简短；正文注意微信对 HTML 与外链的限制。

## 步骤 B：用 Seedance（Seedream）生成图片

1. **术语**：产品线中视频常称 Seedance，图片多对应 **Seedream**；以用户接入文档中的「文生图」模型名为准。
2. 用 `SEEDANCE_API_KEY` 调用服务商 REST/SDK（火山方舟、兼容聚合 API 等），为 **封面** 与 **段落配图** 分别下发生图 prompt；封面比例建议贴近微信习惯（如横版 2.35:1 或官方素材说明中的推荐尺寸），避免极小分辨率导致拒稿。
3. 从响应中取 `image_url` 或 base64，**下载为本地文件** 再上传微信素材；不要在未上传前把第三方临时 URL 长期写死进终稿（URL 可能过期）。
4. 多张图时串行或限流请求，避免触发服务商 QPS；失败时退化为少图或纯文字草稿。

## 步骤 C：微信公众平台发布

1. `access_token`：缓存响应中的过期时间，预留刷新余量；遇 `40001` 等 token 类错误可刷新后 **仅重试一次**。

2. **素材**：`thumb_media_id` 需按文档上传 **封面** 类永久/临时素材；正文内图片按「图文内图片上传」等接口得到可嵌入 URL（以当前文档为准）。

3. **草稿**：`articles` 中 `content` 为 HTML 字符串；`show_cover_pic`、`content_source_url` 等按运营需求填写。

4. **发布**：在具备权限的账号上调用发布相关接口；若用户仅要「保存草稿」，跳过发布步骤并返回 `media_id` 供后台继续编辑。

详细字段表与边界情况见本目录 [reference.md](reference.md)。

## 失败处理（简表）

| 现象 | 动作 |
|------|------|
| DeepSeek 429/5xx | 退避重试；缩小输出长度 |
| 图片接口失败 | 降级无图或单封面；仍保存草稿 |
| 微信 `40054` 等素材类错误 | 检查格式、大小、类型；重传 |
| 发布权限不足 | 明确提示账号类型/接口范围；不要反复重试 |

## 与用户项目的协同

若仓库内已有 `wechat-mp-auto-publish` 根目录 [SKILL.md](../../SKILL.md)，**微信侧细节以该文件为补充**；本 skill 专注 **OpenClaw 门禁元数据** 以及 **DeepSeek + Seedance** 与主流程的编排顺序。
