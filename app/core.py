# -*- coding: utf-8 -*-
"""物归 · 核心数据与规则层（零依赖）。

包含：SQLite 建表与种子数据、口语查询的规则改写、硬过滤、规则打分。
模型相关的能力在 llm.py，这里只放“不依赖模型也能跑”的那一半。
"""
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "data.db"
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ISO = "%Y-%m-%d %H:%M"

# ------------------------------------------------------------------ 词表
SUBJECTS = ["耳机", "水杯", "保温杯", "雨伞", "校园卡", "充电宝", "钥匙", "笔记本",
            "鼠标", "数据线", "眼镜", "书包", "手表", "帽子", "书"]
COLORS = ["白色", "黑色", "蓝色", "红色", "灰色", "绿色", "粉色", "紫色", "黄色",
          "棕色", "藏青", "透明", "米白"]

SYNONYMS = {
    "耳机": ["耳机", "耳麦", "airpods", "蓝牙耳机", "无线耳机", "有线耳机", "耳塞"],
    "水杯": ["水杯", "杯子", "保温杯", "水壶", "茶壶"],
    "保温杯": ["保温杯", "水杯", "杯子", "水壶"],
    "雨伞": ["雨伞", "伞", "遮阳伞"],
    "校园卡": ["校园卡", "学生卡", "一卡通", "卡"],
    "充电宝": ["充电宝", "移动电源", "电池"],
    "钥匙": ["钥匙", "钥匙扣", "门禁卡"],
    "笔记本": ["笔记本", "本子", "记事本"],
    "书": ["书", "教材", "课本"],
}


def _norm(s):
    return (s or "").strip().replace("　", " ")


def same_domain(a, b):
    """判断两个类别是否同域（耳机 vs 耳塞 算同域）。"""
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    for canon, words in SYNONYMS.items():
        if (a in words or a == canon) and (b in words or b == canon):
            return True
    return a in b or b in a


def detect_subject(text):
    for canon, words in SYNONYMS.items():
        if any(w in text for w in words):
            return canon
    return ""


def detect_color(text):
    for c in COLORS:
        if c in text:
            return c
    if "白" in text:
        return "白色"
    if "黑" in text:
        return "黑色"
    return ""


def detect_place(text):
    m = re.search(r"([0-9一二三四五六七八九十]+)\s*教", text)
    if m:
        num = m.group(1)
        zh = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
              "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}
        return zh.get(num, num) + "教"
    for kw in ["图书馆", "体育馆", "食堂", "宿舍", "实验楼", "行政楼", "操场"]:
        if kw in text:
            return kw
    return ""


def detect_window(text, base=None):
    """把“昨天下午”“前天”折算成日期区间。"""
    base = base or datetime.now()
    today = base.replace(hour=0, minute=0, second=0, microsecond=0)
    offset = None
    afternoon = "下午" in text or "傍晚" in text
    evening = "晚上" in text
    morning = "上午" in text or "早上" in text

    if "今天" in text:
        offset = 0
    elif "昨天" in text:
        offset = 1
    elif "前天" in text:
        offset = 2
    elif "上周" in text:
        offset = 7

    if offset is None:
        start = today - timedelta(days=3)
        return start, today + timedelta(days=1)

    day = today - timedelta(days=offset)
    if afternoon:
        return day + timedelta(hours=12), day + timedelta(hours=18)
    if evening:
        return day + timedelta(hours=18), day + timedelta(hours=23)
    if morning:
        return day + timedelta(hours=6), day + timedelta(hours=12)
    return day, day + timedelta(days=1)


def rewrite_query(query):
    """规则版查询改写：模型不可用时的兜底，也是最稳定的那一路。"""
    q = _norm(query)
    subject = detect_subject(q)
    color = detect_color(q)
    place = detect_place(q)
    start, end = detect_window(q)
    tokens = [t for t in re.split(r"[\s，。、,;；]+", q) if len(t) >= 2]
    missing = []
    if not subject:
        missing.append("物品类别")
    if not place:
        missing.append("大致地点")
    return {
        "subject": subject,
        "color": color,
        "place": place,
        "time_from": start.strftime(ISO),
        "time_to": end.strftime(ISO),
        "keywords": tokens[:6],
        "missing": missing,
    }


# ------------------------------------------------------------------ 数据库
@contextmanager
def conn():
    """每次用完必须关闭：Windows 下未关闭的连接会锁住库文件，导致重置失败。"""
    c = sqlite3.connect(DB_PATH, timeout=5)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT, brand TEXT, color TEXT, features TEXT,
    found_at TEXT, place TEXT, hidden_feature TEXT,
    status TEXT DEFAULT 'in_store',
    visibility TEXT DEFAULT 'public',
    image TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER, questions TEXT, answers TEXT,
    score REAL, code TEXT, result TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT, action TEXT, target TEXT, payload TEXT, created_at TEXT
);
"""

SEED = [
    dict(subject="耳机", brand="Apple", color="白色", features=["入耳式", "盒面有卡通猫贴纸"],
         days=-1, hhmm="16:20", place="3教101", hidden="耳机盒背面有一张卡通猫贴纸"),
    dict(subject="耳机", brand="unknown", color="白色", features=["有线", "3.5mm 接口"],
         days=-1, hhmm="18:05", place="2教305", hidden="线材上缠了一圈透明胶"),
    dict(subject="保温杯", brand="Thermos", color="黑色", features=["500ml", "杯盖有划痕"],
         days=-2, hhmm="09:30", place="图书馆2楼", hidden="杯底贴了一张姓名贴"),
    dict(subject="雨伞", brand="unknown", color="藏青", features=["折叠伞", "伞柄有挂绳"],
         days=-3, hhmm="17:10", place="1教大厅", hidden="伞柄上挂了一个小铃铛"),
    dict(subject="校园卡", brand="unknown", color="透明", features=["卡套", "背面有小卡片"],
         days=0, hhmm="10:10", place="3教201", hidden="卡套是透明的，背面夹了一张社团小卡片"),
    dict(subject="充电宝", brand="小米", color="白色", features=["10000mAh", "侧面裂纹"],
         days=-2, hhmm="15:40", place="4教302", hidden="侧面有一道裂纹，贴了胶带"),
    dict(subject="钥匙", brand="unknown", color="银色", features=["三个钥匙", "金属小熊扣"],
         days=-4, hhmm="12:00", place="体育馆门口", hidden="钥匙扣是个金属小熊"),
    dict(subject="笔记本", brand="unknown", color="蓝色", features=["A5", "硬壳"],
         days=-3, hhmm="14:00", place="图书馆3楼", hidden="第一页写了课程名和学号后四位"),
]


def init_db(force=False):
    if force and DB_PATH.exists():
        for _ in range(10):
            try:
                DB_PATH.unlink()
                break
            except PermissionError:
                time.sleep(0.15)
    with conn() as c:
        c.executescript(SCHEMA)
        n = c.execute("SELECT COUNT(*) AS n FROM items").fetchone()["n"]
    if n == 0:
        seed()


def reset_db():
    """清空业务数据并重新播种（演示前的“一键复原”）。"""
    with conn() as c:
        for t in ("claims", "logs", "items"):
            c.execute(f"DELETE FROM {t}")
        c.execute("DELETE FROM sqlite_sequence")
    seed()


def seed():
    now = datetime.now()
    for d in SEED:
        day = (now + timedelta(days=d["days"])).replace(second=0, microsecond=0)
        hh, mm = d["hhmm"].split(":")
        found = day.replace(hour=int(hh), minute=int(mm))
        create_item({
            "subject": d["subject"], "brand": d["brand"], "color": d["color"],
            "features": d["features"], "place": d["place"],
            "hidden_feature": d["hidden"], "found_at": found.strftime(ISO),
        })
    log("system", "seed", "items", {"count": len(SEED)})


def create_item(fields):
    with conn() as c:
        cur = c.execute(
            "INSERT INTO items (subject, brand, color, features, found_at, place,"
            " hidden_feature, status, visibility, image, created_at)"
            " VALUES (?,?,?,?,?,?,?,'in_store','public',?,?)",
            (fields.get("subject", ""), fields.get("brand", "unknown"),
             fields.get("color", ""), json.dumps(fields.get("features", []), ensure_ascii=False),
             fields.get("found_at", datetime.now().strftime(ISO)),
             fields.get("place", ""), fields.get("hidden_feature", ""),
             fields.get("image", ""), datetime.now().strftime(ISO)))
        return get_item(cur.lastrowid)


def _row2item(r):
    if r is None:
        return None
    d = dict(r)
    d["features"] = json.loads(d.get("features") or "[]")
    return d


def get_item(item_id):
    with conn() as c:
        return _row2item(c.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone())


def list_items(status=None):
    sql = "SELECT * FROM items"
    args = ()
    if status:
        sql += " WHERE status=?"
        args = (status,)
    sql += " ORDER BY found_at DESC"
    with conn() as c:
        return [_row2item(r) for r in c.execute(sql, args).fetchall()]


def save_image(data_url):
    """把 data:image/...;base64,xxx 落盘，返回可访问路径。"""
    if not data_url or "," not in data_url:
        return ""
    head, b64 = data_url.split(",", 1)
    ext = ".png"
    if "jpeg" in head or "jpg" in head:
        ext = ".jpg"
    import base64
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return ""
    name = f"{uuid.uuid4().hex[:12]}{ext}"
    (UPLOAD_DIR / name).write_bytes(raw)
    return f"/uploads/{name}"


def log(actor, action, target, payload=None):
    with conn() as c:
        c.execute("INSERT INTO logs (actor, action, target, payload, created_at) VALUES (?,?,?,?,?)",
                  (actor, action, str(target), json.dumps(payload or {}, ensure_ascii=False),
                   datetime.now().strftime(ISO)))


def list_logs(limit=30):
    with conn() as c:
        rows = c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------ 匹配
def hard_filter(items, cond):
    """硬条件：在库、类别同域、时间窗内。地点不参与硬过滤，交给打分降权。"""
    out = []
    t_from = datetime.strptime(cond["time_from"], ISO)
    t_to = datetime.strptime(cond["time_to"], ISO)
    t_from -= timedelta(days=2)
    t_to += timedelta(days=2)
    for it in items:
        if it["status"] != "in_store":
            continue
        if cond.get("subject") and not same_domain(cond["subject"], it["subject"]):
            continue
        try:
            found = datetime.strptime(it["found_at"], ISO)
        except Exception:
            found = datetime.now()
        if not (t_from <= found <= t_to):
            continue
        out.append(it)
    return out


def rule_score(item, cond):
    """规则分：类别 0.35、颜色 0.15、地点 0.25、时间 0.15，归一化到 0—1。"""
    total = 0.35 + 0.15 + 0.25 + 0.15
    s = 0.0
    conflicts = []

    if cond.get("subject"):
        if same_domain(cond["subject"], item["subject"]):
            s += 0.35
        else:
            conflicts.append("类别不符")

    if cond.get("color"):
        if cond["color"][:1] in (item.get("color") or ""):
            s += 0.15
        else:
            conflicts.append("颜色不符")

    if cond.get("place"):
        if cond["place"] in (item.get("place") or ""):
            s += 0.25
        else:
            conflicts.append("地点不符")

    try:
        found = datetime.strptime(item["found_at"], ISO)
        t_from = datetime.strptime(cond["time_from"], ISO)
        t_to = datetime.strptime(cond["time_to"], ISO)
        if t_from - timedelta(hours=2) <= found <= t_to + timedelta(hours=2):
            s += 0.15
        else:
            gap = min(abs((found - t_from).total_seconds()), abs((found - t_to).total_seconds()))
            if gap <= 86400 * 3:
                s += 0.07
            conflicts.append("时间不符")
    except Exception:
        pass

    return round(s / total, 3), conflicts


def merge(rule, sem):
    return round(100 * (0.4 * rule + 0.6 * sem), 1)


def keyword_overlap(text, item):
    """极简语义代理：失主口径的词与条目字段的重合度，模型不可用时使用。"""
    hay = " ".join([item.get("subject", ""), item.get("brand", ""), item.get("color", ""),
                    " ".join(item.get("features", [])), item.get("place", "")]).lower()
    words = [w for w in SYNONYMS.get(item.get("subject", ""), [])]
    words += [item.get("color", ""), item.get("place", "")]
    hit = sum(1 for w in words if w and w.lower() in text.lower())
    return min(1.0, hit / max(3, len(words)))
