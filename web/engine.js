/* 物归 · 浏览器端引擎（纯前端演示版）
 *
 * 把 core.py + llm.py 的规则部分搬到 JS，接口形状与 Python 版完全一致，
 * 因此同一份 UI 既能连后端（fetch），也能纯静态跑（本文件）。
 *
 * 适用范围：GitHub Pages 这类只能托管静态文件的场景。
 * 真实模型（千问-VL / Qwen-Max）需要密钥，只能跑在服务端，本文件不涉及。
 */
(function (global) {
  "use strict";

  const ISO = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ` +
    `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;

  const SYNONYMS = {
    "耳机": ["耳机", "耳麦", "airpods", "蓝牙耳机", "无线耳机", "有线耳机", "耳塞"],
    "水杯": ["水杯", "杯子", "保温杯", "水壶", "茶壶"],
    "保温杯": ["保温杯", "水杯", "杯子", "水壶"],
    "雨伞": ["雨伞", "伞", "遮阳伞"],
    "校园卡": ["校园卡", "学生卡", "一卡通", "卡"],
    "充电宝": ["充电宝", "移动电源", "电池"],
    "钥匙": ["钥匙", "钥匙扣", "门禁卡"],
    "笔记本": ["笔记本", "本子", "记事本"],
    "书": ["书", "教材", "课本"]
  };
  const COLORS = ["白色", "黑色", "蓝色", "红色", "灰色", "绿色", "粉色", "紫色",
                  "黄色", "棕色", "藏青", "透明", "米白"];

  function sameDomain(a, b) {
    a = (a || "").trim(); b = (b || "").trim();
    if (!a || !b) return false;
    if (a === b) return true;
    for (const canon in SYNONYMS) {
      const w = SYNONYMS[canon];
      if ((a === canon || w.includes(a)) && (b === canon || w.includes(b))) return true;
    }
    return a.includes(b) || b.includes(a);
  }

  function detectSubject(t) {
    for (const canon in SYNONYMS) {
      if (SYNONYMS[canon].some((w) => t.includes(w))) return canon;
    }
    return "";
  }
  function detectColor(t) {
    for (const c of COLORS) if (t.includes(c)) return c;
    if (t.includes("白")) return "白色";
    if (t.includes("黑")) return "黑色";
    return "";
  }
  function detectPlace(t) {
    const m = t.match(/([0-9一二三四五六七八九十]+)\s*教/);
    if (m) {
      const zh = { "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
                   "六": "6", "七": "7", "八": "8", "九": "9", "十": "10" };
      return (zh[m[1]] || m[1]) + "教";
    }
    for (const kw of ["图书馆", "体育馆", "食堂", "宿舍", "实验楼", "行政楼", "操场"]) {
      if (t.includes(kw)) return kw;
    }
    return "";
  }

  function detectWindow(t) {
    const base = new Date();
    const today = new Date(base.getFullYear(), base.getMonth(), base.getDate());
    let off = null;
    if (t.includes("今天")) off = 0;
    else if (t.includes("昨天")) off = 1;
    else if (t.includes("前天")) off = 2;
    else if (t.includes("上周")) off = 7;

    if (off === null) {
      const s = new Date(today); s.setDate(s.getDate() - 3);
      const e = new Date(today); e.setDate(e.getDate() + 1);
      return [s, e];
    }
    const day = new Date(today); day.setDate(day.getDate() - off);
    const at = (h) => new Date(day.getFullYear(), day.getMonth(), day.getDate(), h);
    if (t.includes("下午") || t.includes("傍晚")) return [at(12), at(18)];
    if (t.includes("晚上")) return [at(18), at(23)];
    if (t.includes("上午") || t.includes("早上")) return [at(6), at(12)];
    return [day, new Date(day.getTime() + 86400000)];
  }

  function rewriteQuery(q) {
    const t = (q || "").trim();
    const [s, e] = detectWindow(t);
    const cond = {
      subject: detectSubject(t), color: detectColor(t), place: detectPlace(t),
      time_from: ISO(s), time_to: ISO(e),
      keywords: t.split(/[\s，。、,;；]+/).filter((x) => x.length >= 2).slice(0, 6),
      missing: []
    };
    if (!cond.subject) cond.missing.push("物品类别");
    if (!cond.place) cond.missing.push("大致地点");
    return cond;
  }

  /* ---------------- 数据 ---------------- */
  const SEED = [
    { subject: "耳机", brand: "Apple", color: "白色", features: ["入耳式", "盒面有卡通猫贴纸"], days: -1, hhmm: "16:20", place: "3教101", hidden: "耳机盒背面有一张卡通猫贴纸" },
    { subject: "耳机", brand: "unknown", color: "白色", features: ["有线", "3.5mm 接口"], days: -1, hhmm: "18:05", place: "2教305", hidden: "线材上缠了一圈透明胶" },
    { subject: "保温杯", brand: "Thermos", color: "黑色", features: ["500ml", "杯盖有划痕"], days: -2, hhmm: "09:30", place: "图书馆2楼", hidden: "杯底贴了一张姓名贴" },
    { subject: "雨伞", brand: "unknown", color: "藏青", features: ["折叠伞", "伞柄有挂绳"], days: -3, hhmm: "17:10", place: "1教大厅", hidden: "伞柄上挂了一个小铃铛" },
    { subject: "校园卡", brand: "unknown", color: "透明", features: ["卡套", "背面有小卡片"], days: 0, hhmm: "10:10", place: "3教201", hidden: "卡套是透明的，背面夹了一张社团小卡片" },
    { subject: "充电宝", brand: "小米", color: "白色", features: ["10000mAh", "侧面裂纹"], days: -2, hhmm: "15:40", place: "4教302", hidden: "侧面有一道裂纹，贴了胶带" },
    { subject: "钥匙", brand: "unknown", color: "银色", features: ["三个钥匙", "金属小熊扣"], days: -4, hhmm: "12:00", place: "体育馆门口", hidden: "钥匙扣是个金属小熊" },
    { subject: "笔记本", brand: "unknown", color: "蓝色", features: ["A5", "硬壳"], days: -3, hhmm: "14:00", place: "图书馆3楼", hidden: "第一页写了课程名和学号后四位" }
  ];

  const KEY = "guiwu.db.v1";
  let DB = null;

  function blank() {
    return { items: [], claims: [], logs: [], seq: 0 };
  }

  function seed() {
    const db = blank();
    const now = new Date();
    SEED.forEach((d) => {
      const day = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      day.setDate(day.getDate() + d.days);
      const [hh, mm] = d.hhmm.split(":").map(Number);
      day.setHours(hh, mm, 0, 0);
      db.seq += 1;
      db.items.push({
        id: db.seq, subject: d.subject, brand: d.brand, color: d.color,
        features: d.features.slice(), found_at: ISO(day), place: d.place,
        hidden_feature: d.hidden, status: "in_store", visibility: "public",
        image: "", created_at: ISO(new Date())
      });
    });
    db.logs.push(logRow("system", "seed", "items", { count: SEED.length }));
    return db;
  }

  function logRow(actor, action, target, payload) {
    return { id: Date.now() + Math.floor(Math.random() * 1000), actor, action,
             target: String(target), payload: payload || {}, created_at: ISO(new Date()) };
  }

  function load() {
    if (DB) return DB;
    try {
      const raw = global.localStorage && global.localStorage.getItem(KEY);
      if (raw) {
        const d = JSON.parse(raw);
        if (d && Array.isArray(d.items) && d.items.length) { DB = d; return DB; }
      }
    } catch (e) { /* 隐私模式下 localStorage 可能不可用，退化为内存态 */ }
    DB = seed();
    return DB;
  }

  function save() {
    try {
      if (global.localStorage) global.localStorage.setItem(KEY, JSON.stringify(DB));
    } catch (e) { /* 超出配额就只在内存里跑，不影响演示 */ }
  }

  function publicView(it) {
    return { id: it.id, subject: it.subject, brand: it.brand, color: it.color,
             features: it.features, found_at: it.found_at, place: it.place,
             status: it.status, image: it.image };
  }

  /* ---------------- 匹配 ---------------- */
  function hardFilter(cond) {
    const from = new Date(cond.time_from.replace(/-/g, "/"));
    const to = new Date(cond.time_to.replace(/-/g, "/"));
    from.setDate(from.getDate() - 2);
    to.setDate(to.getDate() + 2);
    return load().items.filter((it) => {
      if (it.status !== "in_store") return false;
      if (cond.subject && !sameDomain(cond.subject, it.subject)) return false;
      const found = new Date(it.found_at.replace(/-/g, "/"));
      return found >= from && found <= to;
    });
  }

  function ruleScore(it, cond) {
    const total = 0.35 + 0.15 + 0.25 + 0.15;
    let s = 0;
    const conflicts = [];
    if (cond.subject) {
      if (sameDomain(cond.subject, it.subject)) s += 0.35; else conflicts.push("类别不符");
    }
    if (cond.color) {
      if (it.color && it.color.indexOf(cond.color[0]) >= 0) s += 0.15;
      else conflicts.push("颜色不符");
    }
    if (cond.place) {
      if (it.place && it.place.indexOf(cond.place) >= 0) s += 0.25;
      else conflicts.push("地点不符");
    }
    const found = new Date(it.found_at.replace(/-/g, "/"));
    const from = new Date(cond.time_from.replace(/-/g, "/"));
    const to = new Date(cond.time_to.replace(/-/g, "/"));
    const pad = 7200000;
    if (found >= new Date(from.getTime() - pad) && found <= new Date(to.getTime() + pad)) {
      s += 0.15;
    } else {
      const gap = Math.min(Math.abs(found - from), Math.abs(found - to));
      if (gap <= 86400000 * 3) s += 0.07;
      conflicts.push("时间不符");
    }
    return [Math.round((s / total) * 1000) / 1000, conflicts];
  }

  function merge(rule, sem) {
    return Math.round(100 * (0.4 * rule + 0.6 * sem) * 10) / 10;
  }

  function overlap(text, it) {
    const words = (SYNONYMS[it.subject] || []).concat([it.color || "", it.place || ""]);
    const hit = words.filter((w) => w && text.indexOf(w) >= 0).length;
    return Math.min(1, hit / Math.max(3, words.length));
  }

  function reasonFor(cond, it, conflicts, matched) {
    if (conflicts.length) {
      const head = matched.length ? matched.join("、") + "一致" : "部分特征吻合";
      return `${head}；${conflicts.join("、")}，建议核对`;
    }
    const found = new Date(it.found_at.replace(/-/g, "/"));
    const from = new Date(cond.time_from.replace(/-/g, "/"));
    const hours = Math.round(Math.abs(found - from) / 3600000);
    const head = matched.length ? matched.join("、") + "一致" : "特征吻合";
    return head + (hours ? `，时间相差约 ${hours} 小时` : "，时间吻合");
  }

  function rerank(query, cond, pool) {
    return pool.map((it) => {
      const [rule, conflicts] = ruleScore(it, cond);
      let sem = Math.round((0.62 + 0.32 * overlap(query, it)) * 1000) / 1000;
      if (conflicts.length) sem = Math.round(Math.max(0.2, sem - 0.12 * conflicts.length) * 1000) / 1000;
      const matched = [];
      if (cond.subject && sameDomain(cond.subject, it.subject)) matched.push("类别");
      if (cond.color && it.color && it.color.indexOf(cond.color[0]) >= 0) matched.push("颜色");
      if (cond.place && it.place && it.place.indexOf(cond.place) >= 0) matched.push("地点");
      return { id: it.id, rule, sem, score: merge(rule, sem),
               reason: reasonFor(cond, it, conflicts, matched), conflicts };
    }).sort((a, b) => b.score - a.score);
  }

  /* ---------------- 核验 ---------------- */
  const CANON = [["卡通猫", "猫"], ["猫咪", "猫"], ["小猫", "猫"], ["无线", ""],
                 ["蓝牙", ""], ["的时候", ""], ["好像", ""], ["大概", ""], ["应该", ""]];

  function clean(s) {
    s = (s || "").replace(/[^\u4e00-\u9fa5A-Za-z0-9]/g, "");
    CANON.forEach(([a, b]) => { s = s.split(a).join(b); });
    return s;
  }

  function judge(expect, answer) {
    const exp = clean(expect), ans = clean(answer);
    if (ans.length < 2) return { equivalent: false, confidence: 0.2, note: "回答为空" };
    if (["不知道", "忘了", "不记得", "没注意", "不清楚"].includes(ans)) {
      return { equivalent: false, confidence: 0.1, note: "回答敷衍" };
    }
    const E = new Set(exp), A = new Set(ans);
    let inter = 0;
    E.forEach((ch) => { if (A.has(ch)) inter += 1; });
    const score = 0.5 * (inter / Math.max(1, E.size) + inter / Math.max(1, A.size));
    const ok = score >= 0.6;
    return { equivalent: ok,
             confidence: Math.round(Math.min(0.95, 0.55 + 0.45 * score) * 100) / 100,
             note: ok ? "" : "与要点重合度不足" };
  }

  function makeQuestions(it) {
    const h = it.hidden_feature || "一处只有失主知道的细节";
    return [
      { q: "请描述一下这件物品最特别的地方。", expect: h, weight: 1 },
      { q: "如果只凭一个细节就能认出它，你会说哪一个？", expect: h, weight: 1 },
      { q: "这件物品上有没有贴纸、划痕或挂件？分别在哪里？", expect: h, weight: 1 }
    ];
  }

  function newCode() {
    const pick = (n) => Array.from({ length: n },
      () => "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"[Math.floor(Math.random() * 32)]).join("");
    return `${pick(3)}-${pick(3)}`;
  }

  /* ---------------- 路由 ---------------- */
  function handle(path, body) {
    const db = load();
    const p = path.split("?")[0];
    const isGet = body === null || body === undefined;
    const B = isGet ? {} : body;

    if (p === "/api/health") {
      return { ok: true, mode: "demo", items: db.items.length,
               server_time: ISO(new Date()) };
    }

    if (p === "/api/items" && isGet) {
      const items = db.items.slice().sort((a, b) => (a.found_at < b.found_at ? 1 : -1));
      return { ok: true, items: items.map(publicView) };
    }

    if (p === "/api/logs" && isGet) {
      return { ok: true, logs: db.logs.slice().reverse().slice(0, 30) };
    }

    let m = p.match(/^\/api\/items\/(\d+)$/);
    if (m && isGet) {
      const it = db.items.find((x) => x.id === Number(m[1]));
      if (!it) throw new Error("物品不存在");
      return { ok: true, item: publicView(it) };
    }

    m = p.match(/^\/api\/items\/(\d+)\/questions$/);
    if (m) {
      const it = db.items.find((x) => x.id === Number(m[1]));
      if (!it) throw new Error("物品不存在");
      const qs = makeQuestions(it);
      db.seq += 1;
      const claim = { id: db.seq, item_id: it.id, questions: qs, answers: [],
                      score: 0, code: "", result: "pending", created_at: ISO(new Date()) };
      db.claims.push(claim);
      db.logs.push(logRow("student", "claim_start", it.id, { claim: claim.id }));
      save();
      return { ok: true, claim_id: claim.id, questions: qs.map((x) => ({ q: x.q })) };
    }

    if (p === "/api/parse") {
      return { ok: true, fields: {
        subject: "耳机", brand: "unknown", color: "白色",
        features: ["入耳式", "盒面有贴纸"], sensitive: false,
        confidence: 0.55, fallback: true } };
    }

    return routePost(p, B, db);
  }

  function routePost(p, B, db) {
    if (p === "/api/items") {
      if (!B.subject) throw new Error("缺少物品类别");
      db.seq += 1;
      const it = {
        id: db.seq, subject: B.subject, brand: B.brand || "unknown",
        color: B.color || "", features: Array.isArray(B.features) ? B.features : [],
        found_at: B.found_at || ISO(new Date()), place: B.place || "",
        hidden_feature: B.hidden_feature || "", status: "in_store",
        visibility: B.visibility || "public", image: "", created_at: ISO(new Date())
      };
      db.items.push(it);
      db.logs.push(logRow("student", "create", it.id, { subject: it.subject }));
      save();
      return { ok: true, item: publicView(it) };
    }

    if (p === "/api/search") {
      const q = (B.query || "").trim();
      if (q.length < 2) throw new Error("请多描述一点，比如“昨天在 3 教丢了白色耳机”");
      const cond = rewriteQuery(q);
      const ranked = rerank(q, cond, hardFilter(cond)).slice(0, 3);
      db.logs.push(logRow("student", "search", q.slice(0, 40), { hits: ranked.length }));
      save();
      const candidates = ranked.map((r) => {
        const it = db.items.find((x) => x.id === r.id);
        return Object.assign(publicView(it), {
          score: r.score, reason: r.reason, conflicts: r.conflicts, rule: r.rule });
      });
      return { ok: true, conditions: cond, candidates };
    }

    if (p === "/api/verify") {
      const claim = db.claims.find((c) => c.id === B.claim_id);
      if (!claim) throw new Error("核验记录不存在");
      if (claim.result !== "pending") throw new Error("该核验已完成，请重新发起");
      const it = db.items.find((x) => x.id === claim.item_id);
      const answers = B.answers || [];
      let correct = 0;
      const confs = [];
      const detail = [];
      claim.questions.forEach((q, i) => {
        const r = judge(q.expect, answers[i] || "");
        detail.push({ q: q.q, answer: answers[i] || "", equivalent: r.equivalent,
                      confidence: r.confidence });
        if (r.equivalent) correct += 1;
        confs.push(r.confidence);
      });
      const avg = Math.round((confs.reduce((a, b) => a + b, 0) / Math.max(1, confs.length)) * 100) / 100;
      const passed = correct >= 2 && avg >= 0.7;
      claim.answers = answers;
      claim.score = avg;
      claim.result = passed ? "passed" : "failed";
      claim.code = passed ? newCode() : "";
      db.logs.push(logRow("student", "verify", claim.item_id,
        { claim: claim.id, correct, avg, passed }));
      save();
      const expires = new Date(Date.now() + 86400000);
      return { ok: true, passed, correct, confidence: avg,
               code: claim.code, expires_at: ISO(expires), detail,
               item: it ? publicView(it) : null,
               message: passed ? "核验通过，请凭认领码到保管点领取"
                 : "未通过核验：答对题数或置信度未达阈值，已记录一次尝试，可转人工复核" };
    }

    if (p === "/api/redeem") {
      const code = (B.code || "").trim().toUpperCase();
      if (!code) throw new Error("请输入认领码");
      const claim = db.claims.filter((c) => c.code === code).pop();
      if (!claim) throw new Error("认领码不存在");
      if (claim.result === "claimed") throw new Error("该认领码已被使用");
      const it = db.items.find((x) => x.id === claim.item_id);
      if (!it) throw new Error("物品不存在");
      if (it.status !== "in_store") throw new Error("该物品已不在库");
      claim.result = "claimed";
      it.status = "claimed";
      db.logs.push(logRow("admin", "redeem", it.id, { code }));
      save();
      return { ok: true, item: publicView(it), message: "已核销，物品状态：已认领" };
    }

    if (p === "/api/logs") {
      return { ok: true, logs: db.logs.slice().reverse().slice(0, 30) };
    }

    if (p === "/api/reset") {
      DB = seed();
      save();
      return { ok: true, items: DB.items.length };
    }

    throw new Error("未知接口：" + p);
  }

  const ENGINE = { handle, _reset: () => { DB = seed(); save(); return DB; } };
  if (typeof module !== "undefined" && module.exports) module.exports = ENGINE;
  else global.ENGINE = ENGINE;
})(typeof window !== "undefined" ? window : globalThis);
