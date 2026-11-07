# -*- coding: utf-8 -*-
"""把 workbuddy-pkg 打包成可直接上传 WorkBuddy 开放平台的 zip，并做本地预检。

预检项对齐平台解析器的硬规则：
  1) SKILL.md 必须在包根层
  2) frontmatter 8 个必填字段齐全
  3) version 必须三段式 x.y.z
  4) examples_zh / examples_en 各不超过 3 条
  5) name 小写连字符
  6) 值里不能出现「半角冒号 + 空格」（YAML 会当成嵌套键）
  7) zip 总大小 <= 3MB
用法：python build_workbuddy.py
"""
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "workbuddy-pkg")
DIST = os.path.join(HERE, "dist")

REQUIRED = ["name", "display_name", "display_name_en", "description",
            "description_zh", "description_en", "version", "author"]
PACK_FILES = ["SKILL.md", "README.md", "CHANGELOG.md", "LICENSE",
              "scripts/bookvideo.py", "references/api-contract.md",
              "references/troubleshooting.md", "assets/icon.png"]
MAX_BYTES = 3 * 1024 * 1024

errors, warns = [], []


def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None, "SKILL.md 开头没有 --- 包裹的 frontmatter"
    body = m.group(1)
    data = {}
    for ln in body.splitlines():
        if not ln.strip() or ln.strip().startswith("#"):
            continue
        if ":" not in ln:
            continue
        k, v = ln.split(":", 1)          # 只在第一个冒号切分，值里可以再有冒号
        data[k.strip()] = v.strip()
    return data, None


def main():
    skill_md = os.path.join(PKG, "SKILL.md")
    if not os.path.isfile(skill_md):
        print("FAIL: 包根层没有 SKILL.md")
        return 1
    text = open(skill_md, encoding="utf-8").read()
    data, err = parse_frontmatter(text)
    if err:
        print("FAIL:", err)
        return 1

    for k in REQUIRED:
        if not data.get(k):
            errors.append("缺少必填字段：%s" % k)

    ver = (data.get("version") or "").strip('"')
    if not re.match(r"^\d+\.\d+\.\d+$", ver):
        errors.append("version 不是三段式：%r" % ver)

    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", (data.get("name") or "").strip('"')):
        errors.append("name 不符合小写连字符规范：%r" % data.get("name"))

    for key in ("examples_zh", "examples_en"):
        raw = data.get(key)
        if not raw:
            errors.append("缺少 %s" % key)
            continue
        try:
            lst = json.loads(raw)
            if not isinstance(lst, list) or not lst:
                errors.append("%s 不是非空数组" % key)
            elif len(lst) > 3:
                errors.append("%s 有 %d 条，平台上限 3 条" % (key, len(lst)))
        except Exception as e:  # noqa: BLE001
            errors.append("%s 不是合法 JSON 数组：%s" % (key, e))

    # 值里出现半角冒号+空格：平台解析易失败
    for k, v in data.items():
        inner = v.strip('"').strip("'")
        if ": " in inner:
            errors.append("字段 %s 的值里有「半角冒号+空格」，会触发 YAML 解析错误：%s" % (k, inner[:60]))

    # 必需文件
    for rel in PACK_FILES:
        if not os.path.isfile(os.path.join(PKG, rel)):
            errors.append("缺少文件：%s" % rel)

    # 脚本可编译（用 py_compile 直接编译，别经 shell 拼路径）
    py = os.path.join(PKG, "scripts", "bookvideo.py")
    if os.path.isfile(py):
        import py_compile
        import tempfile
        try:
            py_compile.compile(py, cfile=os.path.join(tempfile.gettempdir(), "bv_pkg_check.pyc"),
                               doraise=True)
        except Exception as e:  # noqa: BLE001
            errors.append("scripts/bookvideo.py 编译失败：%s" % e)

    if errors:
        print("=== 预检未通过 ===")
        for e in errors:
            print(" -", e)
        return 1

    os.makedirs(DIST, exist_ok=True)
    zpath = os.path.join(DIST, "bookvideo-%s.zip" % ver)
    if os.path.isfile(zpath):
        os.remove(zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in PACK_FILES:
            z.write(os.path.join(PKG, rel), arcname=rel)
    size = os.path.getsize(zpath)
    if size > MAX_BYTES:
        print("FAIL: zip 超过 3MB：%.2f MB" % (size / 1048576.0))
        return 1

    print("=== 预检通过 ===")
    print("字段：%s" % ", ".join("%s=%s" % (k, data.get(k)) for k in REQUIRED))
    print("版本：%s" % ver)
    print("打包：%s" % zpath)
    print("大小：%.1f KB（上限 3MB）" % (size / 1024.0))
    with zipfile.ZipFile(zpath) as z:
        print("内容：")
        for n in z.namelist():
            print("  -", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
