/* 浏览器引擎的 Node 冒烟测试：确认静态版与 Python 版结果一致。
 * 运行：node test_engine.js
 */
const E = require("./engine.js");

let pass = 0, total = 0;
function t(name, cond, extra) {
  total++;
  if (cond) { pass++; console.log(`  [OK]   ${name}${extra ? "  " + extra : ""}`); }
  else console.log(`  [FAIL] ${name}${extra ? "  " + extra : ""}`);
}
function call(p, b) { return E.handle(p, b === undefined ? null : b); }

const h = call("/api/health");
t("健康检查", h.ok === true, `mode=${h.mode} items=${h.items}`);

call("/api/reset", {});
t("重置后 8 条", call("/api/items").items.length === 8);

const s = call("/api/search", { query: "昨天下午在3教丢了个白色无线耳机" });
const c = s.candidates;
t("条件解析", s.conditions.subject === "耳机" && s.conditions.place === "3教",
  JSON.stringify(s.conditions));
t("返回候选", c.length > 0, `${c.length} 条`);
console.log("         " + c.map(x => `#${x.id} ${x.subject} ${x.score}%`).join(" | "));
t("Top-1 分数与 Python 版一致（83.6）", Math.abs(c[0].score - 83.6) < 0.15, String(c[0].score));
t("Top-2 分数与 Python 版一致（65.3）", Math.abs(c[1].score - 65.3) < 0.15, String(c[1].score));
t("候选带理由", c[0].reason.length > 5, c[0].reason);

const itemId = c[0].id;
t("公开视图不含隐藏特征", call(`/api/items/${itemId}`).item.hidden_feature === undefined);

const qa = call(`/api/items/${itemId}/questions`);
t("三道题且不泄答案", qa.questions.length === 3 &&
  qa.questions.every(q => q.expect === undefined));

const bad = call("/api/verify", { claim_id: qa.claim_id, answers: ["不知道", "忘了", "不清楚"] });
t("错误答案被拒", bad.passed === false && bad.code === "");

const qa2 = call(`/api/items/${itemId}/questions`);
const good = call("/api/verify", {
  claim_id: qa2.claim_id,
  answers: ["好像是张卡通猫的贴纸，贴在盒子背面", "就是那个猫咪贴纸", "耳机盒背面有一张卡通猫贴纸"]
});
t("同义表达通过", good.passed === true, `conf=${good.confidence} code=${good.code}`);

const rd = call("/api/redeem", { code: good.code });
t("核销成功", rd.item.status === "claimed");

let dup = false;
try { call("/api/redeem", { code: good.code }); } catch (e) { dup = /已被使用/.test(e.message); }
t("认领码不可重复", dup);

t("操作留痕", call("/api/logs").logs.length > 0);

console.log(`\n  ${pass}/${total} 通过`);
process.exit(pass === total ? 0 : 1);
