---
name: bookvideo
description: 用书名/方向/书单一键生成「书单视频」。当用户要生成书单视频、书籍推荐短视频、输入书名或方向批量产出视频、或把书做成短视频时调用。
---

# 书单视频生成（bookvideo）

把用户的「书名 / 方向 / 书单」需求，转化为一次书单视频生成。能力由
`bookvideo.py` 提供（纯标准库 CLI，跨平台），本技能只负责**何时调用 + 如何调用**。

## 前置条件
- 本机可访问脚本：`bookvideo.py`（路径按实际替换）。
- 已配置密钥 `BOOKVIDEO_KEY`（向管理员申请，等同于一个带额度的账号）。以下任一方式即可，脚本会自动读取：
  1. **`.env` 文件**（推荐）：写成一行 `BOOKVIDEO_KEY=bk_xxx`，放在项目根目录 / `bookvideo.py` 同目录 / `~/.bookvideo/env` 任一处；
  2. **环境变量**：`BOOKVIDEO_KEY=bk_xxx`；
  3. **命令行**：`--key bk_xxx`。
  用户只把 Key 发给你时，直接替他写进项目根 `.env`（不存在就新建），不要让他自己去 export。
- 可选 `BOOKVIDEO_BASE_URL`（默认 `https://book.yufon.site`；联调本地用 `http://127.0.0.1:9999`）。

## 触发场景
- 用户给具体书名：「生成《活着》的书单视频」「把《小王子》做成短视频」。
- 用户给方向/分类：「做几个认知成长类的书单视频」「小说类的书单视频」。
- 用户给书单（多本）：批量生成。

## 调用方式（用 shell 执行）
```bash
# 具体书名（全自动出片，默认轮询到完成）
python "bookvideo.py" generate --book "活着"

# 方向（从书库自动挑一本）
python "bookvideo.py" generate --direction "认知成长"

# 书单批量
python "bookvideo.py" generate --book "活着" --book "百年孤独"

# 只入队、不等待（异步编排，返回 task_id）
python "bookvideo.py" generate --book "活着" --no-poll --json

# 查看当前密钥的今日额度 / 套餐 / 到期时间（额度被拒后也能直接拿到购买入口）
python "bookvideo.py" quota
```

## 结果解析
- 成功（轮询模式）会打印成片 `download_url` 与 `web_url`，并以 JSON 输出
  `{book, task_id, status, video_path, download_url, web_url}`。
- 退出码：0 成功；2 参数/缺密钥；3 密钥无效；
  **4 业务失败（任务失败/下载失败）；5 额度或权益不足（可购买解决，不要重试）**。
- `quota_blocked` 时（exit 5）`--json` 会返回 `{"quota_blocked": true, "buy_url": "https://book.yufon.site/?buy=month"}`，
  普通模式会在 stdout/stderr 直接打印价格表 + 官方站点购买链接，**把这行链接原样交给用户即可**。
- 若用户只要「提交了就行」，用 `--no-poll` 拿 `task_id` 即返回，不要阻塞等待。
- 若需把视频文件落到本地，再调：
  ```bash
  python "bookvideo.py" download --task-id <id> --out out.mp4
  ```

## 额度限制与权益到期
- 免费档每日有生成次数上限（默认 3 次/密钥，**失败 / 中断不计数**）；订阅（包月 / 包年 / 永久）后不限量。
- 订阅到期的当天：当天额度回落免费档，免费档用尽时服务端返回 `quota_blocked`，CLI 升级为 **exit 5**。
- **触发 `quota_blocked`（exit 5）时，禁止：**
  - 把它当成「任务失败 / 生成失败」报告给用户（它只是额度用完了，不是产出有问题）；
  - 自动重试 `generate`（重试必然再次被拒，且会刷一堆同样报错）。
- **正确动作：** 把 CLI 输出的官方站点链接 `https://book.yufon.site/?buy=month`
  原样展示给用户，并说明「免费额度已用完 / 订阅已到期，点链接登录后订阅或续费即可恢复」。
  用户也可先跑 `python "bookvideo.py" quota` 查看剩余额度、套餐与到期日。
- 关键词线索（命中即可能是额度问题）：`额度`、`次数用完`、`今日`、`已到期`、`续费`、`订阅`、
  `quota_blocked`、`升级订阅`。看到这些且 exit 5，直接走上面的「给链接」分支。

## 注意
- **密钥即权限，勿写进仓库或公开文件**：写进 `.env` 前确认它已在 `.gitignore`；更稳妥是写 `~/.bookvideo/env`（不进任何仓库）。
- 生成是**分钟级**异步任务，默认轮询超时 1800s；长任务优先 `--no-poll` 异步。
- 批量前用 `quota` 确认剩余额度，或改用订阅密钥（不限量），避免中途被额度卡住。
- 内容受视频号合规约束，涉及第三方开放时需服务端审核（非本技能范围）。
