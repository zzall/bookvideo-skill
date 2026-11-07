# CHANGELOG

## 1.0.0 — 2026-11-07

首个可公开发布的版本（WorkBuddy 技能市场）。

**新增**
- `apply --email` 子命令：一条命自助申领免费密钥（`POST /api/apply-key`），成功后写入 `~/.bookvideo/env`，装上即可用，不再需要向管理员索取 Key
- `status --task-id` 子命令：分段查询任务进度，配合 `generate --no-poll` 使用，适配有单条命令时长上限的 Agent 环境
- `quota` 子命令：查看今日已用 / 上限、套餐与到期日，批量前先查额度

**改进**
- 无密钥时的提示带完整解法：命令申领、网页申领、`.env` / 环境变量 / `--key` 三种配置方式
- `quota_blocked` 统一升级为 `exit 5`，并打印订阅链接；明确禁止换号绕过
- 批量生成逐条返回 `ok`，修正「退出码 0 但部分书失败」被当成全部成功的问题
- `download` 携带会话 cookie，未登录时明确报错
- `.env` 自动加载（项目根目录 / 脚本同目录 / `~/.bookvideo/env`）
- 自测扩展到 7 项：未登录拦截、登录、申领密钥、生成、轮询、方向选书、下载

**接口**
- 依赖 `https://book.yufon.site`（可用 `--base-url` 或 `BOOKVIDEO_BASE_URL` 指向自建服务）
- 免费档每日 3 条（失败不计数）；订阅（日 / 月 / 年 / 永久）不限量
