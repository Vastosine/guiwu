# -*- coding: utf-8 -*-
"""物归 · 零依赖 Web 服务（Python 标准库）。

启动：  python server.py
然后打开 http://127.0.0.1:8000

接口形状刻意保持 REST 风格，日后要换成 FastAPI，路由表可以一一对应搬过去。
"""
import json
import mimetypes
import os
import random
import re
import string
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import core
import llm

APP_DIR = Path(__file__).resolve().parent
STATIC = APP_DIR / "static"
PORT = int(os.environ.get("PORT", "8000"))

MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript",
        ".css": "text/css", ".png": "image/png", ".jpg": "image/jpeg",
        ".svg": "image/svg+xml", ".ico": "image/x-icon", ".json": "application/json"}


def new_code():
    a = "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
    b = "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{a}-{b}"


def public_view(it):
    """对外视图：按可见性裁剪，绝不返回隐藏特征。"""
    return {
        "id": it["id"], "subject": it["subject"], "brand": it["brand"],
        "color": it["color"], "features": it["features"],
        "found_at": it["found_at"], "place": it["place"],
        "status": it["status"], "image": it["image"],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "Guiwu/0.1"

    # ---------------- 基础 ----------------
    def log_message(self, fmt, *args):
        sys.stdout.write("  %s  %s\n" % (self.log_date_time_string(), fmt % args))

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _err(self, code, msg):
        self._send(code, {"ok": False, "error": msg})

    def _file(self, path: Path):
        if not path.exists() or not path.is_file():
            self._err(404, "not found")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # ---------------- GET ----------------
    def do_GET(self):
        u = urlparse(self.path)
        p = u.path

        if p in ("/", "/index.html"):
            return self._file(STATIC / "index.html")
        if p in ("/admin", "/admin.html"):
            return self._file(STATIC / "admin.html")
        if p.startswith("/static/"):
            return self._file(STATIC / p[len("/static/"):])
        if p.startswith("/uploads/"):
            name = os.path.basename(p)
            return self._file(core.UPLOAD_DIR / name)

        if p == "/api/health":
            return self._send(200, {"ok": True, "mode": llm.MODE,
                                    "items": len(core.list_items()),
                                    "server_time": datetime.now().strftime(core.ISO)})

        if p == "/api/items":
            q = parse_qs(u.query)
            status = (q.get("status") or [None])[0]
            return self._send(200, {"ok": True,
                                    "items": [public_view(i) for i in core.list_items(status)]})

        m = re.match(r"^/api/items/(\d+)$", p)
        if m:
            it = core.get_item(int(m.group(1)))
            if not it:
                return self._err(404, "物品不存在")
            return self._send(200, {"ok": True, "item": public_view(it)})

        m = re.match(r"^/api/items/(\d+)/questions$", p)
        if m:
            return self._make_questions(int(m.group(1)))

        if p == "/api/logs":
            return self._send(200, {"ok": True, "logs": core.list_logs()})

        return self._err(404, "not found")

    # ---------------- POST ----------------
    def do_POST(self):
        p = urlparse(self.path).path
        body = self._body()

        try:
            if p == "/api/parse":
                return self._parse(body)
            if p == "/api/items":
                return self._create(body)
            if p == "/api/search":
                return self._search(body)
            if p == "/api/verify":
                return self._verify(body)
            if p == "/api/redeem":
                return self._redeem(body)
            if p == "/api/reset":
                return self._reset()
        except Exception as e:
            import traceback
            traceback.print_exc()
            core.log("system", "error", p, {"error": str(e)[:200]})
            return self._err(500, f"服务器错误：{e}")

        return self._err(404, "not found")

    # ---------------- 业务 ----------------
    def _parse(self, body):
        image = body.get("image") or ""
        fields = llm.parse_item(image)
        core.log("student", "parse", "-", {"subject": fields.get("subject")})
        return self._send(200, {"ok": True, "fields": fields})

    def _create(self, body):
        image = body.pop("image", "")
        img_path = core.save_image(image) if image else ""
        body["image"] = img_path
        if not body.get("subject"):
            return self._err(400, "缺少物品类别")
        item = core.create_item(body)
        core.log("student", "create", item["id"], {"subject": item["subject"]})
        return self._send(200, {"ok": True, "item": public_view(item)})

    def _search(self, body):
        q = (body.get("query") or "").strip()
        if len(q) < 2:
            return self._err(400, "请多描述一点，比如“昨天在 3 教丢了白色耳机”")
        cond = llm.rewrite(q)
        pool = core.hard_filter(core.list_items(), cond)
        ranked = llm.rerank(q, cond, pool)[:3]
        core.log("student", "search", q[:40], {"hits": len(ranked)})
        cands = []
        for r in ranked:
            it = core.get_item(r["id"])
            v = public_view(it)
            v.update({"score": r["score"], "reason": r["reason"],
                      "conflicts": r["conflicts"], "rule": r["rule"]})
            cands.append(v)
        return self._send(200, {"ok": True, "conditions": cond, "candidates": cands})

    def _make_questions(self, item_id):
        it = core.get_item(item_id)
        if not it:
            return self._err(404, "物品不存在")
        qs = llm.questions(it)
        payload = json.dumps(qs, ensure_ascii=False)
        with core.conn() as c:
            cur = c.execute("INSERT INTO claims (item_id, questions, answers, score, code,"
                            " result, created_at) VALUES (?,?, '',0,'','pending',?)",
                            (item_id, payload, datetime.now().strftime(core.ISO)))
            claim_id = cur.lastrowid
        core.log("student", "claim_start", item_id, {"claim": claim_id})
        return self._send(200, {"ok": True, "claim_id": claim_id,
                                "questions": [{"q": x["q"]} for x in qs]})

    def _verify(self, body):
        claim_id = body.get("claim_id")
        answers = body.get("answers") or []
        with core.conn() as c:
            row = c.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
        if not row:
            return self._err(404, "核验记录不存在")
        if row["result"] != "pending":
            return self._err(409, "该核验已完成，请重新发起")
        qs = json.loads(row["questions"])
        item = core.get_item(row["item_id"])

        correct, confs, detail = 0, [], []
        for i, q in enumerate(qs):
            ans = answers[i] if i < len(answers) else ""
            r = llm.judge(q.get("expect", ""), ans)
            detail.append({"q": q["q"], "answer": ans,
                           "equivalent": r["equivalent"], "confidence": r["confidence"]})
            if r["equivalent"]:
                correct += 1
            confs.append(r["confidence"])

        avg = round(sum(confs) / max(1, len(confs)), 2)
        passed = correct >= 2 and avg >= 0.7
        code = new_code() if passed else ""
        expires = (datetime.now() + timedelta(hours=24)).strftime(core.ISO)

        with core.conn() as c:
            c.execute("UPDATE claims SET answers=?, score=?, code=?, result=?"
                      " WHERE id=?", (json.dumps(answers, ensure_ascii=False), avg, code,
                                      "passed" if passed else "failed", claim_id))
        core.log("student", "verify", item["id"] if item else "-",
                 {"claim": claim_id, "correct": correct, "avg": avg, "passed": passed})

        return self._send(200, {
            "ok": True, "passed": passed, "correct": correct, "confidence": avg,
            "code": code, "expires_at": expires, "detail": detail,
            "item": public_view(item) if item else None,
            "message": "核验通过，请凭认领码到保管点领取" if passed
                       else "未通过核验：答对题数或置信度未达阈值，已记录一次尝试，可转人工复核",
        })

    def _redeem(self, body):
        code = (body.get("code") or "").strip().upper()
        if not code:
            return self._err(400, "请输入认领码")
        with core.conn() as c:
            row = c.execute("SELECT * FROM claims WHERE code=? ORDER BY id DESC", (code,)).fetchone()
        if not row:
            return self._err(404, "认领码不存在")
        if row["result"] == "claimed":
            return self._err(409, "该认领码已被使用")
        item = core.get_item(row["item_id"])
        if not item:
            return self._err(404, "物品不存在")
        if item["status"] != "in_store":
            return self._err(409, "该物品已不在库")
        with core.conn() as c:
            c.execute("UPDATE claims SET result='claimed' WHERE id=?", (row["id"],))
            c.execute("UPDATE items SET status='claimed' WHERE id=?", (item["id"],))
        item = core.get_item(item["id"])          # 重新取一次，返回流转后的状态
        core.log("admin", "redeem", item["id"], {"code": code})
        return self._send(200, {"ok": True, "item": public_view(item),
                                "message": "已核销，物品状态：已认领"})

    def _reset(self):
        core.reset_db()
        core.log("admin", "reset", "all", {})
        return self._send(200, {"ok": True, "items": len(core.list_items())})


def main():
    core.init_db()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("=" * 56)
    print("  物归 · 校园失物智能招领平台（原型）")
    print(f"  模式：{'真实模型（DashScope）' if llm.MODE == 'real' else '规则兜底（未配置 API Key）'}")
    print(f"  学生端  http://127.0.0.1:{PORT}/")
    print(f"  管理端  http://127.0.0.1:{PORT}/admin")
    print(f"  物品数  {len(core.list_items())} 条")
    print("  Ctrl+C 停止")
    print("=" * 56)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
