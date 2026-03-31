---
name: wechat-mp-auto-publish
description: >-
  Automates WeChat Official Account (微信公众号) article workflows using the
  WeChat Open Platform Draft Box and publish APIs—draft creation, media upload,
  and submission. Use when the user asks to 自动发布微信公众号文章, 公众号草稿,
  排版发布, CI 发公众号, or integrate scripting with 微信公众平台接口.
---

# 微信公众号文章自动发布

指导 Agent 在用户已具备 **已认证服务号**（或平台已开放的接口能力）的前提下，通过微信公众平台 **开发接口** 完成「素材/封面 → 草稿 → 发布」的自动化流程。具体是否可调通以账号类型与后台权限为准。

## 前置条件（必须由用户自行确认）

- 公众平台账号已启用 **开发者模式**，具备 **AppID** 与 **AppSecret**（密钥仅保存在环境变量或私密配置，禁止写入仓库）。
- 服务器出口 IP 已在公众平台 **IP 白名单**（若接口要求）。
- 若需 **客服消息 / 模板消息** 等与群发不同的能力，勿与「图文发布」混用；本 skill 聚焦 **草稿箱 + 发布** 链路。
- **thumb_media_id**：图文封面需先上传 **永久素材**（thumb）或按官方文档要求的素材类型获取 `media_id`。

## 安全与合规（强制）

- 不得在代码、日志、Skill 示例中硬编码 `appsecret`、长期 `access_token` 或明文 refresh 凭据。
- `access_token` 应缓存并接近过期再刷新；避免高频重复请求导致接口限流。
- 自动化发布前让用户确认标题、摘要、原文链接、原创声明等文案与法务要求。

## 核心流程（推荐顺序）

1. **获取 `access_token`（客户端凭证）**  
   - 使用 `grant_type=client_credential` 与 `appid`、`secret` 换取；注意缓存与过期时间字段。

2. **上传封面素材（若需要 `thumb_media_id`）**  
   - 按官方「上传图文消息内的图片获取 URL」或「新增永久素材」等文档选择与正文配图、封面一致的接口；得到 `thumb_media_id` 后再组草稿。

3. **新增或更新草稿 `draft/add` / `draft/update`**  
   - 组装 `articles` 数组：`title`、`author`、`digest`、`show_cover_pic`、`content`（支持 HTML 富文本，需符合公众平台规则）、`content_source_url`、`thumb_media_id` 等。
   - 正文内若引用本地图片，需先按文档上传并得到可用 URL 或 media_id（以当前平台文档为准）。

4. **发布**  
   - 在账号已具备对应发布能力时，调用官方 **发布** 相关接口（例如将草稿 `media_id` 提交发布——具体路径与字段名以微信公众平台当前文档为准）。  
   - 发布失败时解析返回 `errcode` / `errmsg`，区分「限流」「权限」「草稿非法」「封面无效」等，再重试或降级为「仅保存草稿」。

5. **验收**  
   - 在公众平台后台核对草稿/已发列表；抽查移动端排版与外链。

## Agent 执行时的默认实现策略

- **优先使用用户项目内已有封装**（如自建的 `WeChatClient`、配置加载方式）；若无，再用最小可运行的脚本（Node / Python 任一，与用户仓库一致）演示调用链，并把密钥读取为环境变量。
- **错误处理**：所有 HTTP 响应需记录 `errcode`；对 `40001`（token 类）尝试刷新 token 后重试一次，避免死循环。
- **可重复性**：同一篇文章二次发布应使用「更新草稿」或生成新草稿，避免用户误以为已发列表会自动去重。

## 输出物约定

- 若用户要「可重复运行的发布工具」：给出 `README` 级别的用法说明（ env 变量名、一键命令），**不**在文档中粘贴真实密钥。
- 若用户只要单次发布：给出可直接调用的请求步骤与 JSON 模板，并标明哪些字段必须由用户填写。

## 参考（人工核对最新版）

以下链接随微信文档迭代可能变更，实现前应用浏览器打开核对字段与路径：

- [微信公众平台开发文档](https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Overview.html)
- [草稿箱 / 草稿相关能力](https://developers.weixin.qq.com/doc/offiaccount/Draft_Box/Getting_Draft_Box_List.html)（以侧栏中实际「新增草稿」等页面为准）

## 触发词（便于检索）

微信公众号自动发布、`draft/add`、`access_token`、`thumb_media_id`、素材上传、公众平台 IP 白名单。
