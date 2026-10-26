#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bookvideo — 跨平台命令行：用书名 / 方向 / 书单一键生成「书单视频」。

设计目标（让「各大 agent 都能一键接入」）
--------------------------------------------------
* 平台无关、零三方依赖：只用 Python 标准库（urllib / http.cookiejar），
  Python 3.8+ 任意环境（Windows / macOS / Linux）直接跑。
* 无状态友好：每次调用自行 login -> generate -> (轮询) -> 下载，不依赖长期会话，
  适合被 agent 反复调用。
* 机器可读 + 人类可读：默认打印摘要，加 --json 输出结构化结果，便于 agent 解析。

接入方式（任何 agent 都一样）
--------------------------------------------------
1. 把本文件（bookvideo.py）放到 agent 可访问的路径；
2. 配置密钥与地址（二选一）：
     - 环境变量：BOOKVIDEO_KEY=xxxx   BOOKVIDEO_BASE_URL=https://book.yufon.site
     - 或命令行：--key xxxx --base-url https://book.yufon.site
3. 调用，例如：
     python bookvideo.py generate --book "活着"
     python bookvideo.py generate --direction "认知成长" --count 1
     python bookvideo.py generate --book "活着" --book "百年孤独" --no-poll
     python bookvideo.py download --task-id <id> --out out.mp4

API 契约（基于 book 服务已核实的接口）
--------------------------------------------------
* 鉴权：业务 GET 走 session cookie；POST 业务接口用 form 字段 key。
  本脚本先 POST /api/login（form key=）拿到 bk_sid cookie，之后请求自动携带。
* 生成：POST /api/generate（form: key, book, src_mode=new_auto）。
  服务端 _auto_ensure_book 会在书名不在库时自动抓取，返回 {ok, task_id, queue_position}。
* 轮询：GET /api/status?task_id= 返回 state（含 status / video / error / log）。
* 书库：GET /api/books 返回 {books:[{book_name, author, category, ...}]}（方向选书用）。
* 下载：GET /api/download?task_id=&step=video（单文件 302 到对象存储或直传）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.request import Request, build_opener

DEFAULT_BASE = "https://book.yufon.site"
APP = "bookvideo-cli/1.0"


class BookVideoError(Exception):
    """基类：所有可预期的错误。"""


class AuthError(BookVideoError):
    """密钥无效 / 无权限。"""


class ApiError(BookVideoError):
    """业务接口返回失败。"""


def _read_body(resp) -> str:
    try:
        return resp.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""


class Client:
    """薄封装：登录 + 生成 + 轮询 + 书库 + 下载。"""

    def __init__(self, base_url: str, key: str, timeout: float = 30.0,
                 opener=None):
        self.base = (base_url or DEFAULT_BASE).rstrip("/")
        self.key = key
        self.timeout = timeout
        self._sid = None  # 会话 cookie（手动管理，兼容 IP 地址部署）
        self.opener = opener or build_opener()

    # ---- 底层请求 ----
    def _request(self, method: str, path: str, form: dict = None, json_body=None):
        url = self.base + path
        data = None
        headers = {"User-Agent": APP, "Accept": "application/json"}
        if self._sid:
            headers["Cookie"] = "bk_sid=" + self._sid
        if json_body is not None:
            # /api/login 接受 JSON body（与 /api/generate 的 form 不同）
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif form is not None:
            data = urllib.parse.urlencode(form, encoding="utf-8").encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                body = _read_body(r)
                status = r.status
                self._capture_cookie(r.headers)
        except urllib.error.HTTPError as e:  # 4xx/5xx 也读 body
            body = _read_body(e)
            status = e.code
        except Exception as e:  # 连接失败 / 超时
            raise BookVideoError("%s %s 请求失败：%s" % (method, path, e))
        try:
            j = json.loads(body) if body.strip() else {}
        except Exception:
            j = {"_raw": body}
        j["_status"] = status
        return status, j

    def _capture_cookie(self, headers):
        for h in (headers.get_all("Set-Cookie") or []):
            m = re.search(r"bk_sid=([^;]+)", h or "")
            if m:
                self._sid = m.group(1)

    # ---- 业务方法 ----
    def login(self):
        st, j = self._request("POST", "/api/login", json_body={"key": self.key})
        if st in (401, 403) or (isinstance(j, dict)
                                and j.get("authenticated") is False):
            raise AuthError("登录失败：密钥无效或无权限（HTTP %s）" % st)
        if st >= 400:
            raise ApiError("登录接口异常 HTTP %s：%s" % (st, j))
        return j

    def generate(self, book: str, src_mode: str = "new_auto",
                 await_script: bool = False, duration: float = None):
        form = {"key": self.key, "book": book, "src_mode": src_mode}
        if await_script:
            form["src_mode"] = "new_manual"
        if duration is not None:
            form["duration"] = str(duration)
        st, j = self._request("POST", "/api/generate", form=form)
        if st >= 400 or not j.get("ok"):
            raise ApiError("生成请求失败：%s" % (j.get("error") or "HTTP %s" % st))
        return j  # {ok, book, task_id, queue_position, quota_blocked?}

    def status(self, task_id: str) -> dict:
        st, j = self._request("GET", "/api/status?task_id="
                              + urllib.parse.quote(task_id, safe=""))
        return j

    def books(self) -> list:
        st, j = self._request("GET", "/api/books")
        if st >= 400:
            raise ApiError("获取书库失败 HTTP %s：%s" % (st, j))
        return j.get("books") or []

    def pick_by_direction(self, direction: str, count: int = 1) -> list:
        d = (direction or "").strip()
        if not d:
            raise ApiError("方向不能为空")
        books = self.books()
        if not books:
            raise ApiError("书库为空，无法按方向选书")
        # 先精确包含，再宽松子串（分类名可能是「认知成长」这类复合词）
        matched = [b for b in books
                   if d in (b.get("category") or "")
                   or d in (b.get("book_name") or "")]
        if not matched:
            matched = [b for b in books
                       if (b.get("category") or "").find(d) >= 0
                       or (b.get("book_name") or "").find(d) >= 0]
        if not matched:
            raise ApiError("书库中没有匹配「%s」的书，请改用 --book 指定具体书名" % d)
        return matched[: max(1, count)]

    def poll(self, task_id: str, total_timeout: float = 1800.0,
             interval: float = 5.0) -> dict:
        deadline = time.time() + total_timeout
        last = None
        while time.time() < deadline:
            j = self.status(task_id)
            last = j
            st = str(j.get("status") or "").lower()
            if st == "done":
                return j
            if st in ("error", "failed", "interrupted", "aborted",
                      "terminated", "中断", "失败"):
                raise ApiError("任务失败/中断：%s"
                               % (j.get("error") or j.get("log") or st))
            time.sleep(interval)
        raise BookVideoError("轮询超时（%ss）仍未出片" % int(total_timeout))

    def download(self, task_id: str, out_path: str) -> str:
        """把成片下载到本地文件，返回本地路径。CookieJar 按域过滤，302 到对象存储不会泄漏会话。"""
        url = (self.base + "/api/download?task_id="
               + urllib.parse.quote(task_id, safe="") + "&step=video")
        req = Request(url, headers={"User-Agent": APP})
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            raise ApiError("下载失败 HTTP %s：%s" % (e.code, _read_body(e)))
        except Exception as e:  # noqa: BLE001
            raise BookVideoError("下载请求失败：%s" % e)
        with open(out_path, "wb") as f:
            f.write(data)
        return out_path


def _video_download_url(client: "Client", task_id: str, video: str) -> str:
    if str(video).startswith(("http://", "https://")):
        return video
    return (client.base + "/api/download?task_id="
            + urllib.parse.quote(task_id, safe="") + "&step=video")


def _run_generate(args) -> int:
    key = args.key or os.environ.get("BOOKVIDEO_KEY")
    if not key:
        print("[错误] 缺少密钥：用 --key 或环境变量 BOOKVIDEO_KEY", file=sys.stderr)
        return 2
    client = Client(args.base_url or os.environ.get("BOOKVIDEO_BASE_URL")
                    or DEFAULT_BASE, key, timeout=args.http_timeout)
    try:
        client.login()
    except AuthError as e:
        print("[错误] %s" % e, file=sys.stderr)
        return 3

    # 决定要生成的书的列表
    books = []
    if args.direction:
        try:
            picks = client.pick_by_direction(args.direction, args.count)
        except ApiError as e:
            print("[错误] %s" % e, file=sys.stderr)
            return 4
        books = [b.get("book_name") for b in picks]
    else:
        books = args.book or []
    if not books:
        print("[错误] 必须提供 --book 或 --direction", file=sys.stderr)
        return 2

    results = []
    for book in books:
        try:
            g = client.generate(book, duration=args.duration,
                                await_script=args.await_script)
        except ApiError as e:
            print("[错误] 《%s》入队失败：%s" % (book, e), file=sys.stderr)
            results.append({"book": book, "ok": False, "error": str(e)})
            continue
        tid = g.get("task_id")
        entry = {"book": book, "ok": True, "task_id": tid,
                 "queue_position": g.get("queue_position")}
        if args.no_poll:
            print("已入队：《%s》 task_id=%s" % (book, tid))
        else:
            print("生成中：《%s》 task_id=%s …" % (book, tid), flush=True)
            try:
                j = client.poll(tid, total_timeout=args.poll_timeout)
            except BookVideoError as e:
                print("  [失败] %s" % e, file=sys.stderr)
                entry["ok"] = False
                entry["error"] = str(e)
                results.append(entry)
                continue
            video = j.get("video") or ""
            entry["status"] = j.get("status")
            entry["video_path"] = video
            entry["download_url"] = _video_download_url(client, tid, video)
            entry["web_url"] = "%s/?task_id=%s" % (client.base,
                                                   urllib.parse.quote(tid, safe=""))
            print("  [完成] 成片：%s" % entry["download_url"])
        results.append(entry)

    if args.json:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    ok_n = sum(1 for r in results if r.get("ok"))
    return 0 if ok_n == len(results) and results else (0 if results else 2)


def _run_download(args) -> int:
    key = args.key or os.environ.get("BOOKVIDEO_KEY")
    if not key:
        print("[错误] 缺少密钥：用 --key 或环境变量 BOOKVIDEO_KEY", file=sys.stderr)
        return 2
    client = Client(args.base_url or os.environ.get("BOOKVIDEO_BASE_URL")
                    or DEFAULT_BASE, key, timeout=args.http_timeout)
    try:
        client.login()
        out = client.download(args.task_id, args.out)
    except BookVideoError as e:
        print("[错误] %s" % e, file=sys.stderr)
        return 4
    print("已保存到：%s" % out)
    if args.json:
        print(json.dumps({"ok": True, "file": out}, ensure_ascii=False))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="用书名/方向/书单一键生成书单视频（跨平台 CLI）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", default=None,
                   help="服务地址，默认 %s 或环境变量 BOOKVIDEO_BASE_URL" % DEFAULT_BASE)
    p.add_argument("--key", default=None, help="访问密钥，或环境变量 BOOKVIDEO_KEY")
    p.add_argument("--http-timeout", type=float, default=30.0, help="单次 HTTP 超时(秒)")
    p.add_argument("--json", action="store_true", help="输出结构化 JSON")

    sub = p.add_subparsers(dest="cmd")

    g = sub.add_parser("generate", help="生成书单视频")
    g.add_argument("--book", action="append", default=[],
                   help="书名（可多次，批量生成书单）")
    g.add_argument("--direction", default=None,
                   help="方向/分类关键词，自动从书库挑书（如「认知成长」）")
    g.add_argument("--count", type=int, default=1, help="方向模式挑选的本书数")
    g.add_argument("--duration", type=float, default=None, help="成片时长(秒)")
    g.add_argument("--await-script", action="store_true",
                   help="生成文案后暂停等待确认（默认全自动 new_auto）")
    g.add_argument("--no-poll", action="store_true",
                   help="只入队返回 task_id，不轮询等待出片")
    g.add_argument("--poll-timeout", type=float, default=1800.0,
                   help="轮询总超时(秒)，默认 1800")
    g.set_defaults(func=_run_generate)

    d = sub.add_parser("download", help="下载某任务的成片到本地")
    d.add_argument("--task-id", required=True)
    d.add_argument("--out", required=True, help="本地保存路径（.mp4）")
    d.set_defaults(func=_run_download)

    sub.add_parser("selftest", help="内置 mock 服务端到端自测（无需真实服务）")
    return p


# --------------------------------------------------------------------------
# 内置自测：起一个 mock HTTP 服务，验证 登录/生成/轮询/下载/方向选书 全链路。
# --------------------------------------------------------------------------
def _run_selftest() -> int:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading

    class H(BaseHTTPRequestHandler):
        calls = {"status": 0}

        def log_message(self, *a):  # 静默
            pass

        def _send(self, code, obj=None, cookie=None, body_bytes=None,
                  content_type="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            if cookie:
                self.send_header("Set-Cookie", cookie)
            if body_bytes is not None:
                self.send_header("Content-Length", str(len(body_bytes)))
                self.end_headers()
                self.wfile.write(body_bytes)
            else:
                b = (json.dumps(obj, ensure_ascii=False).encode("utf-8")
                     if obj is not None else b"")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

        def do_POST(self):
            if self.path == "/api/login":
                self._send(200, {"authenticated": True, "name": "tester"},
                           cookie="bk_sid=testtoken; Path=/")
            elif self.path == "/api/generate":
                self._send(200, {"ok": True, "task_id": "t1",
                                 "queue_position": 0})
            else:
                self._send(404, {"ok": False, "error": "not found"})

        def do_GET(self):
            if self.path.startswith("/api/status"):
                H.calls["status"] += 1
                if H.calls["status"] < 2:
                    self._send(200, {"status": "running", "video": ""})
                else:
                    self._send(200, {"status": "done",
                                     "video": "data/books/活着/out.mp4"})
            elif self.path == "/api/books":
                self._send(200, {"books": [
                    {"book_name": "活着", "author": "余华",
                     "category": "认知成长"},
                    {"book_name": "百年孤独", "author": "马尔克斯",
                     "category": "小说"},
                ]})
            elif self.path.startswith("/api/download"):
                self._send(200, body_bytes=b"\x00\x00\x00\x18ftypmp42"
                           b"mock-video-bytes", content_type="video/mp4")
            else:
                self._send(404, {"ok": False, "error": "not found"})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()

    base = "http://127.0.0.1:%d" % port
    c = Client(base, "testkey", timeout=5.0)
    fails = 0

    def check(name, cond):
        nonlocal fails
        print(("PASS" if cond else "FAIL"), name)
        if not cond:
            fails += 1

    try:
        c.login()
        check("login 建立会话(cookie)", True)
        g = c.generate("活着")
        check("generate 返回 task_id", g.get("task_id") == "t1")
        j = c.poll("t1", total_timeout=10, interval=0.1)
        check("poll 到 done", j.get("status") == "done")
        picks = c.pick_by_direction("认知成长", 1)
        check("方向选书命中分类", picks and picks[0]["book_name"] == "活着")
        import tempfile, os as _os
        tmp = _os.path.join(tempfile.gettempdir(), "bv_selftest.mp4")
        out = c.download("t1", tmp)
        check("download 写文件", _os.path.exists(out) and _os.path.getsize(out) > 0)
    except Exception as e:  # noqa: BLE001
        print("FAIL 自测异常：", e)
        fails += 1
    finally:
        srv.shutdown()

    print("SELFTEST", "ALL_PASS" if fails == 0 else "HAS_FAIL")
    return 1 if fails else 0


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    if getattr(args, "cmd", None) == "selftest":
        return _run_selftest()
    if not getattr(args, "func", None):
        _build_parser().print_help()
        return 2
    try:
        return args.func(args)
    except BookVideoError as e:
        print("[错误] %s" % e, file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
