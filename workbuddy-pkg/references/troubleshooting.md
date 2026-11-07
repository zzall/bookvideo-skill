# 常见失败与处置

## 缺密钥（exit 2）

终端会打印「需要配置密钥」并给出两种领取方式。处置：

```bash
python scripts/bookvideo.py apply --email 用户邮箱
```

成功后自动写入 `~/.bookvideo/env`。**不要虚构 Key，也不要跳过这一步直接报生成失败。**

## 鉴权失败（exit 3）

Key 无效、被重置或已过期。让用户到 `https://book.yufon.site` 登录核对；确认无效就重新 `apply`（同一邮箱可能受判重限制）。不要循环重试。

## 额度不足（exit 5）

`quota_blocked`：今日免费额度用完，或订阅到期回落免费档。终端会打印订阅链接 `https://book.yufon.site/?buy=month`。

处置：把链接给用户，说明「今日额度已用完 / 套餐已到期」。**禁止**换邮箱、换设备、改指纹重复申领；**禁止**把额度不足当"生成失败"反复重试。

## 轮询超时

`--poll-timeout` 默认 1800 秒。超时不代表任务失败，处置：

```bash
python scripts/bookvideo.py generate --book "书名" --no-poll   # 先拿 task_id
python scripts/bookvideo.py status --task-id <id>              # 之后分段查询
python scripts/bookvideo.py download --task-id <id> --out o.mp4
```

Agent 环境的单条命令通常有时长上限，长任务一律走 `--no-poll` + `status`。

## 下载失败 / 链接过期

成片地址是对象存储签名 URL，有过期时间。重新 `status` 取新地址；`download` 需要有效会话，脚本会自动 `login`，不要手动拼 URL 绕过。

## 任务失败（error / failed / interrupted / aborted）

读 `status` 返回的 `error` 原文并转告用户。同一本书连续失败 2 次就停下，不要继续重试；可能是书名无法抓取素材，建议换书名或方向词。

## 网络与服务不可达

- 确认能访问 `https://book.yufon.site`
- 自建服务用 `--base-url` 指定；本地联调可用 `http://127.0.0.1:9999`
- 代理环境下如遇证书问题，优先修代理配置，不要关闭证书校验

## 批量部分失败

`generate` 批量时退出码仍可能是 0。必须逐条检查 `results[].ok` 与 `results[].error`，把失败的书名单独列出反馈，不能因为退出码 0 就报告"全部成功"。

## 环境自检

```bash
python scripts/bookvideo.py selftest
```

内置 mock 服务端，不联网、不消耗额度，7 项 PASS 结尾 `SELFTEST ALL_PASS` 为正常。失败说明本机 Python 环境或文件权限有问题，先修环境再谈生成。
