# bookvideo 后端接口契约

服务默认地址 `https://book.yufon.site`，可用 `--base-url` 或环境变量 `BOOKVIDEO_BASE_URL` 覆盖。

所有请求带 `User-Agent: bookvideo-cli/1.0`；登录后业务 GET 依赖 `bk_sid` 会话 cookie，POST 业务接口同时带 form 字段 `key`。

## 接口一览

| 方法 | 路径 | 入参 | 返回 | 用途 |
|---|---|---|---|---|
| POST | `/api/login` | JSON `{"key": "..."}` | `{authenticated, name}` + `Set-Cookie: bk_sid` | 建立会话 |
| POST | `/api/apply-code` | JSON `{"email": "..."}` | `{ok, ttl}`；未配 SMTP 时 `{ok:false, no_verify:true, error}` | 发送邮箱验证码 |
| POST | `/api/apply-key` | JSON `{"email", "fp", "code"}` | `{ok, key, daily_limit, note}` | 公开自助申领免费密钥（配了 SMTP 必须带 `code`） |
| POST | `/api/generate` | form `key` / `book` / `src_mode` / 可选 `duration` | `{ok, task_id, queue_position}` | 提交生成任务 |
| GET | `/api/status?task_id=` | — | `{status, video, error, log}` | 查询任务状态 |
| GET | `/api/books` | — | `{books:[{book_name, author, category}]}` | 书库（方向选书用） |
| GET | `/api/me` | — | `{authenticated, quota:{used, limit, plan, paid_until, unlimited}, is_admin}` | 当前密钥额度 |
| GET | `/api/plans` | — | `{plans:[{plan, amount, days}]}` | 公开套餐表 |
| GET | `/api/download?task_id=&step=video` | — | 302 到对象存储直链 | 下载成片（需会话） |

## 关键字段

- `status`：`queued` / `running` / `done` / `error`。失败态还包括 `failed`、`interrupted`、`aborted`、`terminated`。
- `video`：`done` 后的成片地址，可能是对象存储签名 URL，有时效。
- `quota_blocked`：`/api/generate` 额度不足时返回 `ok:false` + `quota_blocked:true`（兼容 HTTP 402）。
- `/api/apply-key` 限频：按 邮箱 / 设备指纹 / IP 段 判重；超限返回 429 + `need_pay:true`。
- 邮箱验证：服务端配了 SMTP（`SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` / `SMTP_FROM`，465 端口加 `SMTP_SSL=1`）时，`/api/apply-key` 必须带正确 `code`，否则 400；验证码 10 分钟有效、一次一用、同邮箱 60 秒才能重发、每天最多 5 次。未配 SMTP 时自动降级为上面三重限频，避免线上申领挂掉。
- **CLI 不代注册**：`bookvideo.py apply` 只打印申请页地址，不调用 `/api/apply-key`。申领必须由本人在页面完成，否则邮箱校验、设备指纹、IP 频次拿到的都不是申请者的真实信息。

## 额度模型（服务端口径）

- 免费额度：每个密钥每日成功生成上限 3 条，失败 / 中断不计数（`APPLY_DAILY_LIMIT = 3`）
- 付费套餐：`day` / `month` / `year` / `life`，订阅期内不限量
- `trial` 体验单每 Key 仅一次，过期回落免费额度
- 订阅到期当天回落免费档；用尽即 `quota_blocked`

## CLI 退出码

| 码 | 含义 | 处置 |
|---|---|---|
| 0 | 已执行（批量需逐条看 `ok`） | 正常 |
| 2 | 参数错误 / 缺少密钥 | 先 `apply --email`，再重跑 |
| 3 | 鉴权失败（Key 无效 / 过期） | 让用户确认或重新申领，不要重试 |
| 4 | 请求失败（入队 / 方向无匹配 / 下载） | 读错误原文，最多重试 2 次 |
| 5 | 额度 / 权益不足 | 把订阅链接给用户，禁止重试、禁止换号绕过 |
