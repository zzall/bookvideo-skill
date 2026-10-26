---
name: bookvideo
description: 用书名/方向/书单一键生成「书单视频」。当用户要生成书单视频、书籍推荐短视频、输入书名或方向批量产出视频、或把书做成短视频时调用。
---

# 书单视频生成（bookvideo）

把用户的「书名 / 方向 / 书单」需求，转化为一次书单视频生成。能力由
`bookvideo.py` 提供（纯标准库 CLI，跨平台），本技能只负责**何时调用 + 如何调用**。

## 前置条件
- 本机可访问脚本：`bookvideo.py`（路径按实际替换）。
- 已配置环境变量 `BOOKVIDEO_KEY`（密钥向管理员索取，等同于一个带额度的账号）。
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
```

## 结果解析
- 成功（轮询模式）会打印成片 `download_url` 与 `web_url`，并以 JSON 输出
  `{book, task_id, status, video_path, download_url, web_url}`。
- 退出码：0 成功；2 参数/缺密钥；3 密钥无效；4 业务失败（额度/任务失败/下载失败）。
- 若用户只要「提交了就行」，用 `--no-poll` 拿 `task_id` 即返回，不要阻塞等待。
- 若需把视频文件落到本地，再调：
  ```bash
  python "bookvideo.py" download --task-id <id> --out out.mp4
  ```

## 注意
- **密钥即权限，勿写进仓库或公开文件**；走环境变量。
- 生成是**分钟级**异步任务，默认轮询超时 1800s；长任务优先 `--no-poll` 异步。
- 每日有生成额度（默认 3 次/密钥），批量前确认额度或改用 VIP 密钥。
- 内容受视频号合规约束，涉及第三方开放时需服务端审核（非本技能范围）。
