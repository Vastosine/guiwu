# -*- coding: utf-8 -*-
"""端到端冒烟测试：不依赖任何第三方库，直接打 HTTP 接口。

用法（服务已启动）：  python smoke.py
"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"
OK, FAIL = "  [OK]  ", "  [FAIL]"


def call(path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def check(name, cond, extra=""):
    print(f"{OK if cond else FAIL} {name}{('  ' + extra) if extra else ''}")
    return bool(cond)


def main():
    passed = 0
    total = 0

    def t(name, cond, extra=""):
        nonlocal passed, total
        total += 1
        passed += 1 if check(name, cond, extra) else 0

    h = call("/api/health")
    t("健康检查", h.get("ok"), f"mode={h['mode']} items={h['items']}")

    r = call("/api/reset", {})
    t("重置演示数据", r.get("items") == 8, f"{r.get('items')} 条")

    q = "昨天下午在3教丢了个白色无线耳机"
    s = call("/api/search", {"query": q})
    cands = s.get("candidates", [])
    t("口语寻回返回候选", len(cands) > 0, f"{len(cands)} 条")
    t("条件解析出地点与类别",
      s["conditions"].get("place") == "3教" and s["conditions"].get("subject") == "耳机",
      json.dumps(s["conditions"], ensure_ascii=False))
    if cands:
        top = cands[0]
        t("Top-1 命中 3 教耳机", "3教" in top["place"] and "耳机" in top["subject"],
          f"#{top['id']} {top['subject']} {top['score']}%")
        t("候选带可读理由", len(top["reason"]) >= 6, top["reason"])
        t("分数可区分", len(cands) < 2 or cands[0]["score"] > cands[-1]["score"])

    item_id = cands[0]["id"]
    item = call(f"/api/items/{item_id}")["item"]
    t("公开视图不含隐藏特征", "hidden_feature" not in item)

    qa = call(f"/api/items/{item_id}/questions")
    t("生成 3 道核验题", len(qa["questions"]) == 3)
    t("题目不泄露答案要点", all("expect" not in x for x in qa["questions"]))

    # 错误答案 → 应被拒绝
    bad = call("/api/verify", {"claim_id": qa["claim_id"],
                               "answers": ["不知道", "忘了", "不清楚"]})
    t("错误答案被拒绝", bad["passed"] is False and bad["code"] == "",
      f"答对 {bad['correct']}/3")

    qa2 = call(f"/api/items/{item_id}/questions")
    # 换成失主的口语说法（同义、加语气词），检验判分不会误拒
    right_answers = ["好像是张卡通猫的贴纸，贴在盒子背面"] * 2 + ["耳机盒背面有一张卡通猫贴纸"]
    good = call("/api/verify", {"claim_id": qa2["claim_id"], "answers": right_answers})
    t("正确答案通过并发放认领码", good["passed"] is True and len(good["code"]) == 7,
      f"code={good['code']} conf={good['confidence']}")

    if good["passed"]:
        rd = call("/api/redeem", {"code": good["code"]})
        t("管理端核销成功", rd["item"]["status"] == "claimed")
        try:
            call("/api/redeem", {"code": good["code"]})
            t("认领码不可重复核销", False)
        except Exception as e:
            t("认领码不可重复核销", "已被使用" in str(e) or "409" in str(e))

    items = call("/api/items")["items"]
    t("核销后状态已流转", any(i["status"] == "claimed" for i in items))

    logs = call("/api/logs")["logs"]
    t("操作留痕", len(logs) > 0, f"{len(logs)} 条")

    print(f"\n  {passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
