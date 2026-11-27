# -*- coding: utf-8 -*-
"""物归 · 模型网关。

一个原则：模型是“增强”，不是“依赖”。
- 设了 DASHSCOPE_API_KEY 就走真实模型；
- 没设、或调用失败（超时/限流/返回非法 JSON），自动降级到规则实现。
这样答辩现场断网也能演示完整闭环。
"""
import json
import os
import re
import urllib.request
from datetime import datetime

import core

API_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
API_KEY = os.environ.get("DASHSCOPE_API_KEY", "").strip()
VISION_MODEL = os.environ.get("QWEN_VL_MODEL", "qwen-vl-max")
TEXT_MODEL = os.environ.get("QWEN_TEXT_MODEL", "qwen-max")

MODE = "real" if API_KEY else "mock"


# ------------------------------------------------------------------ 通用
def _post(payload, timeout=60):
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {API_KEY}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _loads(text):
    """模型偶尔会裹一层 ```json，这里做一次宽容解析。"""
    if not text:
        return {}
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(t[start:end + 1])
        except Exception:
            return {}
    return {}


def _chat(system, user, model=TEXT_MODEL, temp=0.2):
    return _post({
        "model": model,
        "temperature": temp,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    })


# ------------------------------------------------------------------ 提示词
P_PARSE = """你是校园失物招领系统的入库助手，把一张物品照片转成结构化条目。

【硬性规则】
1. 只填写照片中可见的信息，看不到的字段一律填 "unknown"，禁止根据常识推断。
2. brand 只有出现清晰 Logo 或型号文字时才填写，否则 unknown。
3. 不要输出解释性文字，只输出 JSON。
4. 若画面中没有可识别的物品，subject 填 "none"。

【字段】
subject: 物品类别（耳机/水杯/保温杯/雨伞/校园卡/充电宝/钥匙/笔记本/书/其他）
brand: 品牌或 unknown
color: 主色，多色用 / 分隔
features: 3 条以内显著特征，每条不超过 12 字（划痕、贴纸、挂件、磨损）
sensitive: 画面是否出现姓名/学号/手机号/证件号（true/false）
confidence: 0—1 之间的小数

【输出】严格 JSON：
{"subject":"","brand":"","color":"","features":[],"sensitive":false,"confidence":0.0}"""

P_REWRITE = """现在是 {now}，校区为 {campus}。用户在校园失物系统里描述丢失的物品：
「{query}」

请改写成检索条件，只输出 JSON：
{{"subject":"","color":"","place":"","time_from":"YYYY-MM-DD HH:MM",
 "time_to":"YYYY-MM-DD HH:MM","keywords":[],"missing":[]}}

要求：
- “昨天下午”“上周三”等相对时间必须结合 {now} 折算成具体区间。
- 用户没提到的字段留空字符串，不要猜；没提到的关键信息列进 missing。
- keywords 给 2—4 个可用于模糊匹配的中文词，覆盖同义表达（无线耳机/蓝牙耳机/airpods）。
- 地点只保留楼栋或区域名，不要编造房间号。"""

P_RERANK = """你是失物匹配的判定员。失主描述：「{query}」
检索条件：{cond}

候选物品（JSON 数组）：{cands}

请逐条判断“是否为同一件物品”，输出 JSON 数组，每项：
{{"id":1,"sem":0—1,"reason":"不超过 40 字的中文理由","conflicts":["地点不符"]}}

要求：
- 类别不同直接给 sem ≤ 0.2。
- 地点或时间冲突必须写进 conflicts，并相应降低 sem。
- sem 要能拉开差距，不要都落在 0.7—0.8。
- reason 必须说明“为什么推荐”或“哪里对不上”，禁止只写“相似”。
- 只输出 JSON 数组。"""

P_QUESTION = """拾得者对物品的隐藏特征描述是：「{hidden}」
物品类别：{subject}

请基于该特征生成 3 道核验问题，用于确认申请人是否为真正的失主。
输出 JSON：{{"questions":[{{"q":"","expect":"","weight":1}}]}}

要求：
- 必须是开放题，不能是“是不是”“有没有”这类是非题（防止逐题试错）。
- expect 写“标准答案要点”，而不是逐字答案，便于后续做语义等价判断。
- 三道题的信息量要有梯度，至少一道需要回忆细节（位置、颜色、数量）。
- 不得在问题中出现物品的完整答案，避免申请人直接从题目里抄。"""

P_JUDGE = """标准答案要点：「{expect}」
申请人回答：「{answer}」

判断两者在语义上是否指向同一事实，输出 JSON：
{{"equivalent":true,"confidence":0.0,"note":""}}

判定原则：
- 允许口语化与同义词（猫咪≈卡通猫）、模糊数量（“好像两三个”≈“两个”）。
- 方向、位置、颜色这类关键信息矛盾时判 false。
- 回答明显敷衍（“不知道”“忘了”）判 false。
- confidence 低于 0.6 时，在 note 中写“建议人工复核”。"""


# ------------------------------------------------------------------ 规则兜底
_CANON = [("卡通猫", "猫"), ("猫咪", "猫"), ("小猫", "猫"), ("无线", ""),
          ("蓝牙", ""), ("的时候", ""), ("好像", ""), ("大概", ""), ("应该", "")]


def _clean(s):
    s = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", s or "")
    for a, b in _CANON:
        s = s.replace(a, b)
    return s


def _bigrams(s):
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


def _mock_judge(expect, answer):
    """规则版语义比对：用字符集合的双向覆盖率近似“说的是不是同一件事”。

    只看单向覆盖率会误判两类情况：答得比标准答案长（“好像是张猫咪贴纸，在背面”）
    会被判低分，答得极短（只说“贴纸”）又能蒙混过关。所以取双向平均。
    """
    exp, ans = _clean(expect), _clean(answer)
    if len(ans) < 2:
        return {"equivalent": False, "confidence": 0.2, "note": "回答为空"}
    if ans in ("不知道", "忘了", "不记得", "没注意", "不清楚"):
        return {"equivalent": False, "confidence": 0.1, "note": "回答敷衍"}
    e, a = set(exp), set(ans)
    inter = e & a
    ce = len(inter) / max(1, len(e))
    ca = len(inter) / max(1, len(a))
    score = 0.5 * (ce + ca)
    ok = score >= 0.6
    return {"equivalent": ok,
            "confidence": round(min(0.95, 0.55 + 0.45 * score), 2),
            "note": "" if ok else "与要点重合度不足"}


def _reason(cond, item, conflicts, matched):
    if conflicts:
        head = "、".join(matched) + "一致" if matched else "部分特征吻合"
        return f"{head}；{'、'.join(conflicts)}，建议核对"
    try:
        found = datetime.strptime(item["found_at"], core.ISO)
        t_from = datetime.strptime(cond["time_from"], core.ISO)
        hours = round(abs((found - t_from).total_seconds()) / 3600)
        tail = f"，时间相差约 {hours} 小时" if hours else "，时间吻合"
    except Exception:
        tail = ""
    head = "、".join(matched) + "一致" if matched else "特征吻合"
    return f"{head}{tail}"


def _mock_rerank(query, cond, cands):
    out = []
    for it in cands:
        rule, conflicts = core.rule_score(it, cond)
        ov = core.keyword_overlap(query, it)
        sem = round(0.62 + 0.32 * ov, 3)
        if conflicts:
            sem = round(max(0.2, sem - 0.12 * len(conflicts)), 3)
        matched = []
        if cond.get("subject") and core.same_domain(cond["subject"], it["subject"]):
            matched.append("类别")
        if cond.get("color") and cond["color"][:1] in (it.get("color") or ""):
            matched.append("颜色")
        if cond.get("place") and cond["place"] in (it.get("place") or ""):
            matched.append("地点")
        out.append({
            "id": it["id"],
            "rule": rule,
            "sem": sem,
            "score": core.merge(rule, sem),
            "reason": _reason(cond, it, conflicts, matched),
            "conflicts": conflicts,
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


def _mock_questions(hidden, subject):
    """三道题都锚在同一个隐藏细节上，只是问法不同。

    规则模式没有真正的推理能力，若三题各问一件事，只能给出笼统的 expect，
    真失主反而会被误拒。锚在同一细节上，知道的人三题都答得出，冒充的人一题都答不像。
    """
    h = hidden or "一处只有失主知道的细节"
    return [
        {"q": "请描述一下这件物品最特别的地方。", "expect": h, "weight": 1},
        {"q": "如果只凭一个细节就能认出它，你会说哪一个？", "expect": h, "weight": 1},
        {"q": "这件物品上有没有贴纸、划痕或挂件？分别在哪里？", "expect": h, "weight": 1},
    ]


# ------------------------------------------------------------------ 对外接口
def parse_item(image_data_url, hint_place=""):
    """图片 → 结构化字段。"""
    if MODE == "real":
        try:
            content = [
                {"type": "text", "text": "请按规则输出这件物品的结构化字段。"},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ]
            raw = _post({"model": VISION_MODEL, "temperature": 0.2,
                         "messages": [{"role": "system", "content": P_PARSE},
                                      {"role": "user", "content": content}]})
            d = _loads(raw)
            if d.get("subject"):
                d.setdefault("features", [])
                d.setdefault("brand", "unknown")
                d.setdefault("confidence", 0.8)
                return d
        except Exception as e:
            core.log("system", "llm_fallback", "parse", {"error": str(e)[:120]})
    # 规则兜底：演示用的兜底结果，真实项目里应提示“请手动填写”
    return {"subject": "耳机", "brand": "unknown", "color": "白色",
            "features": ["入耳式", "盒面有贴纸"], "sensitive": False,
            "confidence": 0.55, "fallback": True}


def rewrite(query):
    if MODE == "real":
        try:
            raw = _chat(P_REWRITE.format(now=datetime.now().strftime("%Y-%m-%d %H:%M"),
                                         campus="杭州电子科技大学下沙校区", query=query),
                        "只输出 JSON，不要解释。")
            d = _loads(raw)
            if d.get("time_from") and d.get("time_to"):
                d.setdefault("keywords", [])
                d.setdefault("missing", [])
                return d
        except Exception as e:
            core.log("system", "llm_fallback", "rewrite", {"error": str(e)[:120]})
    return core.rewrite_query(query)


def rerank(query, cond, cands):
    if not cands:
        return []
    if MODE == "real":
        try:
            brief = [{"id": it["id"], "subject": it["subject"], "brand": it["brand"],
                      "color": it["color"], "features": it["features"],
                      "found_at": it["found_at"], "place": it["place"]} for it in cands]
            raw = _chat(P_RERANK.format(query=query, cond=json.dumps(cond, ensure_ascii=False),
                                        cands=json.dumps(brief, ensure_ascii=False)),
                        "只输出 JSON 数组。")
            arr = _loads(raw)
            if isinstance(arr, dict):
                arr = arr.get("items") or arr.get("results") or []
            by_id = {it["id"]: it for it in cands}
            out = []
            for r in arr:
                it = by_id.get(r.get("id"))
                if not it:
                    continue
                rule, conflicts = core.rule_score(it, cond)
                sem = float(r.get("sem", 0.6))
                merged = sorted(set(conflicts) | set(r.get("conflicts") or []))
                out.append({"id": it["id"], "rule": rule, "sem": sem,
                            "score": core.merge(rule, sem),
                            "reason": r.get("reason") or "特征吻合",
                            "conflicts": merged})
            if out:
                out.sort(key=lambda x: x["score"], reverse=True)
                return out
        except Exception as e:
            core.log("system", "llm_fallback", "rerank", {"error": str(e)[:120]})
    return _mock_rerank(query, cond, cands)


def questions(item):
    if MODE == "real":
        try:
            raw = _chat(P_QUESTION.format(hidden=item.get("hidden_feature", ""),
                                          subject=item.get("subject", "")),
                        "只输出 JSON。")
            d = _loads(raw)
            if isinstance(d, list):
                d = {"questions": d}
            qs = d.get("questions") or []
            if len(qs) >= 3:
                return qs[:3]
        except Exception as e:
            core.log("system", "llm_fallback", "questions", {"error": str(e)[:120]})
    return _mock_questions(item.get("hidden_feature", ""), item.get("subject", ""))


def judge(expect, answer):
    if MODE == "real":
        try:
            d = _loads(_chat(P_JUDGE.format(expect=expect, answer=answer), "只输出 JSON。"))
            if "equivalent" in d:
                return {"equivalent": bool(d["equivalent"]),
                        "confidence": float(d.get("confidence", 0.6)),
                        "note": d.get("note", "")}
        except Exception as e:
            core.log("system", "llm_fallback", "judge", {"error": str(e)[:120]})
    return _mock_judge(expect, answer)
