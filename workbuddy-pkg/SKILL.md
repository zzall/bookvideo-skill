---
name: "bookvideo"
display_name: "书单视频生成"
display_name_en: "Book Video Generator"
description: "用书名、方向或书单生成可直接发布的书单短视频。用户要做书单视频、把某本书做成短视频、按分类批量出片时使用。"
description_zh: "输入书名、方向或书单，自动完成文案、配音、画面与字幕，产出可发布的书单短视频。"
description_en: "Turn a book title, a category, or a reading list into a ready-to-publish book-recommendation short video."
version: 1.0.0
author: "Yufon"
category: "内容创作"
examples_zh: ["用《活着》生成一条书单视频", "做几条认知成长类的书单视频", "给《原则》和《心流》各生成一条视频"]
examples_en: ["Generate a book video for To Live", "Make several cognition-growth book videos", "Generate one video each for Principles and Flow"]
---

# 书单视频生成

把「书名 / 方向 / 书单」变成可直接发布到视频号的书单短视频。文案、配音、画面、字幕由服务端流水线产出；本技能负责申领密钥、提交任务、跟踪进度、下载成片。

## 何时使用

- 用户要做书单视频、荐书短视频、一本书的解读视频
- 用户给出书名（如《活着》），或给出方向词（如「认知成长」「商业思维」）
- 用户要求批量出片、做系列、按书单一次做多条
- 用户要把已生成的任务下载到本地

不适用：剪辑已有视频、写书评图文、直播带货脚本、有声小说录制。

## 前置条件

- Python 3.8+，Windows / macOS / Linux 通用，纯标准库、零第三方依赖
- 首次使用需要一个免费密钥：**打开申请页自助领取**（`bookvideo.py apply` 会给你地址），免费档每天 3 条（失败不计数），不需要联系任何人
- 可访问 `https://book.yufon.site`

脚本位于本技能包 `scripts/bookvideo.py`，命令一律从技能包根目录执行。

## 标准流程

### 第 1 步：确保有密钥（只做一次）

```bash
python scripts/bookvideo.py apply
```

这条命令**不会替你申领**，只打印官方申请页地址（`https://book.yufon.site/skill`）。把链接给用户，让他在浏览器里填邮箱、完成页面上的校验后领取。申领必须由本人完成：服务端按邮箱、设备、网络三重限频，脚本代领等于绕开风控。

领到 Key 后，让用户自己保存（或他把 Key 交给你，由你代写）：

```bash
python scripts/bookvideo.py key --set 用户的Key
```

保存后写入 `~/.bookvideo/env`，后续命令自动读取。已有密钥时也可用 `--key`、环境变量或 `.env` 文件（项目根目录 / 脚本同目录 / `~/.bookvideo/env` 任一），优先级：`--key` > 环境变量 > `.env`。

### 第 2 步：生成

```bash
python scripts/bookvideo.py generate --book "活着" --book "原则"
python scripts/bookvideo.py generate --direction "认知成长" --count 3
```

参数：`--book`（可重复）、`--direction`、`--count`（方向模式挑几本，默认 1）、`--duration`（成片时长秒）、`--no-poll`（只入队不等待）、`--poll-timeout`（等待上限，默认 1800 秒）。

生成通常 2–10 分钟。**执行环境对单条命令有时长限制时，务必加 `--no-poll`**，再用 status 分段查询。

### 第 3 步：查询进度 / 下载

```bash
python scripts/bookvideo.py status --task-id <task_id>
python scripts/bookvideo.py download --task-id <task_id> --out 成片.mp4
```

`status` 的 status 字段：`queued` / `running` / `done` / `error`。`done` 时给出成片地址。遇到 `error`、`failed`、`interrupted`、`aborted` 立即停止轮询，把错误原文转给用户，重试不超过 2 次。

推荐节奏：`--no-poll` 批量入队 → 每 60–120 秒 `status` 一轮 → `done` 后 `download`。

### 第 4 步：查额度

```bash
python scripts/bookvideo.py quota
```

返回今日已用 / 上限、套餐、到期日。批量前先看一眼，避免中途被额度卡住。

## 结果怎么读

- `--json` 是全局参数，也可放在子命令后：`python scripts/bookvideo.py generate --book "活着" --json`
- 生成结果结构：`{"results": [{"book", "ok", "task_id", "queue_position", "status", "video_path", "download_url", "web_url"}]}`
- **以每条 `ok` 为准**：退出码 0 不代表每条都成功（批量部分失败仍返回 0）
- 退出码：`0` 已执行（逐条看 ok）；`2` 参数错误或缺密钥；`3` 鉴权失败（Key 无效）；`4` 请求或下载失败；**`5` 额度 / 权益不足**
- 退出码 5：终端会直接给出订阅链接 `https://book.yufon.site/?buy=month`。**把这个链接给用户，不要当生成失败报告，也不要重试**
- 缺密钥（退出码 2）：先跑第 1 步 `apply`

## 注意事项

- **不要替用户申领**：`apply` 只给申请页地址，真正的领取必须由用户本人在网页完成（邮箱校验 + 设备 + 网络三重限频都在服务端，代领就是绕开风控）
- **不要绕过限频**：换邮箱、换设备、改指纹重复申领一律不做，额度是服务端的成本闸门
- **不要编造密钥**：没有 Key 就引导申领，绝不虚构一个 `bk_xxx` 去调用
- **密钥是个人凭据**：只存 `.env` / `~/.bookvideo/env`，不写进代码、仓库、聊天记录或日志
- **下载链接有时效**：成片是对象存储签名地址，拿到后尽快 `download`；过期就重新 `status` 取新地址
- **服务故障**：默认服务不可达时如实告知失败，不要伪造成功结果；用户有自建服务可用 `--base-url` 指定
- **内容合规**：只做正常书籍内容，违规题材直接拒绝
- **不代发**：本技能只产出成片，不替用户登录视频号或自动发布，发布由用户自己完成
- **长任务不阻塞**：单条命令超时上限小于 2 分钟时，一律 `--no-poll` + `status`

## 深入参考

- `references/api-contract.md`：后端接口、字段、退出码的完整契约
- `references/troubleshooting.md`：常见失败场景与处置口径
