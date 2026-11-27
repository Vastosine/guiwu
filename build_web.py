# -*- coding: utf-8 -*-
"""把 app/static 构建成可托管在 GitHub Pages 的纯静态站（输出到 docs/）。

同一份 UI 源码，两种部署：
- 本地 python server.py  → 走真实接口（可接千问-VL / Qwen-Max）
- 静态站（本脚本输出）   → 走 web/engine.js 的浏览器端规则引擎
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "app" / "static"
OUT = ROOT / "docs"
ENGINE = ROOT / "web" / "engine.js"

INJECT = '\n<script src="engine.js"></script>\n</body>'


def build():
    OUT.mkdir(exist_ok=True)

    index = (SRC / "index.html").read_text(encoding="utf-8")
    index = (index
             .replace('href="/static/app.css"', 'href="app.css"')
             .replace('href="/admin"', 'href="admin.html"')
             .replace("</body>", INJECT))
    (OUT / "index.html").write_text(index, encoding="utf-8")

    admin = (SRC / "admin.html").read_text(encoding="utf-8")
    admin = (admin
             .replace('href="/static/app.css"', 'href="app.css"')
             .replace('href="/"', 'href="index.html"')
             .replace("</body>", INJECT))
    (OUT / "admin.html").write_text(admin, encoding="utf-8")

    shutil.copyfile(SRC / "app.css", OUT / "app.css")
    shutil.copyfile(ENGINE, OUT / "engine.js")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    print("built ->", OUT)
    for f in sorted(OUT.iterdir()):
        print(f"  {f.name:12} {f.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build()
