# bookvideo — 跨 Agent 通用的「书单视频」生成 Skill

> 输入一个书名 / 一个方向 / 一份书单 → 一键生成发到视频号的「书单视频」。
> 能力下沉到一个**平台无关的 Python CLI**（纯标准库，零依赖），任何 Agent（CodeBuddy / Cursor / Claude / 通用脚本）只要能跑 Python，装好密钥即可接入。

---

## 1. 这是什么

- **`bookvideo.py`**：核心 CLI（Python 3.8+，仅用标准库 `urllib`/`http`，跨 Windows / macOS / Linux）。
- **`SKILL.codebuddy.md` / `SKILL.cursor.md` / `SKILL.claude.md`**：各 Agent 平台的薄适配说明（告诉 Agent 何时调、怎么调）。
- 后端依赖一个已部署的 book-video 服务（`book.yufon.site` 或你自托管的实例），负责异步渲染成片。

设计原则：**核心逻辑只在 `bookvideo.py` 一处**，各 Agent 只放一份 `SKILL.md` 指向它，避免重复维护。

---

## 2. 下载 / 获取

### 方式 A：从 GitHub 克隆（推荐，拿最新）

```bash
git clone https://github.com/zzall/book-video.git
# skill 在仓库的 bookvideo-skill/ 目录下
cd book-video/bookvideo-skill
```

### 方式 B：只要单文件

直接把 `bookvideo.py` 拷贝到任意位置即可（它零依赖，不依赖本仓库其他文件）：

```bash
curl -O https://raw.githubusercontent.com/zzall/book-video/main/bookvideo-skill/bookvideo.py
# 或浏览器打开上面的 URL 另存为
```

### 方式 C：接入某个 Agent

把对应 `SKILL.*.md` 复制到该 Agent 的 skills 目录，并确保它能执行 `bookvideo.py`。详见文末「各 Agent 接入」。

---

## 3. 配置（必做）

脚本需要两样东西：**密钥** 与 **服务地址**。

### 3.1 密钥 `BOOKVIDEO_KEY`

向服务管理员索取（或自助申请入口，若已开放）。**密钥即额度账号，等同于可消耗生成次数**，务必保管。

```bash
# 推荐：用环境变量（不要写进脚本 / 仓库）
export BOOKVIDEO_KEY="你的密钥"

# 或在命令里临时给（不推荐长期用）
python bookvideo.py generate --book "活着" --key "你的密钥"
```

### 3.2 服务地址 `BOOKVIDEO_BASE_URL`

```bash
export BOOKVIDEO_BASE_URL="https://book.yufon.site"   # 默认即此，可省略
# 本地联调时改成：
export BOOKVIDEO_BASE_URL="http://127.0.0.1:9999"
```

---

## 4. 正常使用

> 以下命令默认 `BOOKVIDEO_KEY` 已配置，且当前目录能访问 `bookvideo.py`。

### 4.1 指定书名，全自动出片（最常用）

```bash
python bookvideo.py generate --book "活着"
```
脚本会自动：登录 → 入队（书名不在书库会自动抓取）→ 轮询到出片 → 打印成片下载链接。
默认轮询超时 1800s（分钟级渲染，耐心等）。

### 4.2 按「方向 / 分类」自动挑一本

不想指定具体书？给个方向，脚本从书库按分类/书名模糊匹配挑一本生成：

```bash
python bookvideo.py generate --direction "认知成长"
python bookvideo.py generate --direction "小说"
```

### 4.3 批量书单（多本一起）

```bash
python bookvideo.py generate --book "活着" --book "百年孤独" --book "小王子"
```
每本独立任务，分别轮询，最后逐个输出成片链接。

### 4.4 只入队、不等待（异步编排）

当你只是「提交任务」、不想阻塞，用 `--no-poll` 拿到 `task_id` 就返回：

```bash
python bookvideo.py generate --book "活着" --no-poll --json
# 输出 {"results":[{"book":"活着","ok":true,"task_id":"t_xxx",...}]}
```
之后想查进度/取片，用 `task_id` 调状态接口或本脚本后续扩展。

### 4.5 把成片下载到本地文件

```bash
python bookvideo.py download --task-id <task_id> --out 活着.mp4
```
脚本带登录会话下载，落盘到 `out.mp4`。Agent 拿本地路径即可二次处理。

### 4.6 给程序消费（JSON 输出）

加 `--json`，输出结构化结果，便于 Agent / 流水线解析：

```bash
python bookvideo.py generate --book "活着" --json
```
成功后得到：
```json
{
  "book": "活着",
  "ok": true,
  "task_id": "t_xxx",
  "status": "done",
  "video_path": "data/books/活着/v3/out.mp4",
  "download_url": "https://book.yufon.site/api/download?task_id=t_xxx&step=video",
  "web_url": "https://book.yufon.site/?task_id=t_xxx"
}
```

### 4.7 控制成片时长 / 自定义文案

```bash
python bookvideo.py generate --book "活着" --duration 60     # 约 60 秒成片
python bookvideo.py generate --book "活着" --await-script     # 生成文案后暂停，等人工确认再继续
```

---

## 5. 骚操作（高级玩法）

### 5.1 本地联调，不花线上额度
把 `BOOKVIDEO_BASE_URL` 指向本地服务，安全调试脚本本身：
```bash
BOOKVIDEO_BASE_URL=http://127.0.0.1:9999 python bookvideo.py generate --book "测试书" --no-poll
```

### 5.2 多 Agent / 多业务线，用多密钥隔离额度
每个 Agent 或每条业务线发一个独立 `BOOKVIDEO_KEY`（服务侧可设每日上限 / 有效期），各自设环境变量，互不影响、便于成本核算与封禁。

### 5.3 批量生成 + 自动落盘一条龙
写个小循环，把一批书全部生成并下载到本地目录：
```bash
for b in "活着" "百年孤独" "小王子"; do
  tid=$(python bookvideo.py generate --book "$b" --no-poll --json | python -c "import sys,json;print(json.load(sys.stdin)['results'][0]['task_id'])")
  # 稍后轮询到 done 再下载，或用带轮询的 generate 拿 download_url 后 download
  python bookvideo.py download --task-id "$tid" --out "$b.mp4"
done
```

### 5.4 接进自动化流水线
用 `--json` 解析 `task_id`，配合你自己的调度器（cron / Airflow / n8n / Agent 编排）：
提交阶段用 `--no-poll` 拿 id → 调度器定时查状态 → done 后调 `download` 落盘 → 触发后续（发视频号 / 转码 / 归档）。

### 5.5 结合 ffmpeg 二次剪辑 / 合并
下载到本地的 `*.mp4` 可以直接 ffmpeg 处理：加封面、裁黑边、拼接成「合集」、抽帧做缩略图等：
```bash
ffmpeg -i 活着.mp4 -i cover.jpg -map 0:v -map 0:a -map 1:v -disposition:v:1 attached_pic out.mp4
```

### 5.6 长任务别用同步轮询阻塞
成片动辄几分钟。需要长时间稳定运行（如服务器脚本）时，一律用 `--no-poll` 提交，再另起轻量轮询，避免单进程卡 30 分钟。

### 5.7 签名 URL 会过期，及时 download
成片 `download_url` 在远程对象存储模式下是带签名的临时 URL，过期后失效。拿到 `task_id` 后尽快用 `download` 子命令落盘（走服务端会话，不受签名过期限制）。

### 5.8 用「方向」做主题书单 /  weekly 栏目
`--direction` 配合书库分类，可以 weekly 栏目化：「本周认知成长 5 本」「本月小说精选」，脚本挑书 + 生成，你只管排期。

### 5.9 自定义文案质量
默认全自动生成文案（`new_auto`）。若对文案要求高，用 `--await-script` 在生成文案后暂停，人工润色确认后再继续渲染，兼顾质量与自动化。

### 5.10 零依赖部署到任意环境
`bookvideo.py` 只用 Python 标准库，无需 `pip install`。丢到 CI、Docker（`python:slim` 即可）、无网内网机（指向内网服务地址）都能跑。

---

## 6. 各 Agent 接入

| Agent | 做法 |
|---|---|
| **CodeBuddy** | 把 `SKILL.codebuddy.md` 存为 `.codebuddy/skills/bookvideo/SKILL.md`，并确保能执行 `bookvideo.py` + 配 `BOOKVIDEO_KEY`。 |
| **Cursor** | 把 `SKILL.cursor.md` 存为 `.cursor/skills/bookvideo/SKILL.md`（或粘进项目规则）。 |
| **Claude Code** | 把 `SKILL.claude.md` 作为 skill 或 `CLAUDE.md` 片段加载。 |
| **其他 / 通用** | 能跑 Python 就能用：直接调命令，或把本 README 关键段写进系统提示也能工作。 |

`SKILL.*.md` 里写明了触发词、命令模板、返回解析、注意事项，Agent 照做即可。

---

## 7. 退出码

| 码 | 含义 |
|---|---|
| 0 | 全部成功 |
| 2 | 参数错误 / 未提供书或密钥 |
| 3 | 鉴权失败（密钥无效） |
| 4 | 业务失败（额度耗尽 / 任务失败 / 下载失败） |

---

## 8. 安全 & 合规

- **密钥即权限**：`BOOKVIDEO_KEY` 等同于一个可消耗生成额度的账号，**勿提交进仓库 / 勿写进公开可读文件**；用环境变量或 secret 注入。
- **额度**：每个密钥有每日成功生成上限（默认 3，VIP 不限），批量前确认额度。
- **渲染耗时**：分钟级异步；`--poll-timeout` 默认 1800s，按需调大。
- **合规**：生成内容受视频号内容安全约束；开放给第三方前需服务端接入审核（非本脚本范围）。

---

## 9. 自测（无需真实服务）

```bash
python bookvideo.py selftest
# 期望：5 项 PASS，结尾 SELFTEST ALL_PASS
```
内置一个 mock HTTP 服务，验证 登录 / 生成 / 轮询 / 方向选书 / 下载 全链路逻辑。

---

## 10. 命令速查

```bash
python bookvideo.py generate --book "书名"            # 指定书名出片
python bookvideo.py generate --direction "分类"        # 按方向挑书出片
python bookvideo.py generate --book A --book B         # 批量书单
python bookvideo.py generate --book "书名" --no-poll   # 只入队拿 task_id
python bookvideo.py generate --book "书名" --json      # 机器可读输出
python bookvideo.py download --task-id <id> --out o.mp4 # 下载成片
python bookvideo.py selftest                            # 自测
```
