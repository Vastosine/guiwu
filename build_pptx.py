# -*- coding: utf-8 -*-
"""生成《物归 · 项目方案》PPT（16:9，19 页）。"""
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

INK = RGBColor(0x17, 0x32, 0x4D)
ACCENT = RGBColor(0xC9, 0x62, 0x2F)
TEAL = RGBColor(0x2E, 0x7A, 0x72)
GRAY = RGBColor(0x4E, 0x5A, 0x66)
MUTED = RGBColor(0x8B, 0x94, 0x9D)
BLACK = RGBColor(0x1E, 0x2A, 0x33)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CREAM = RGBColor(0xF5, 0xF0, 0xE6)
PAPER = RGBColor(0xFB, 0xF9, 0xF4)
HAIR = RGBColor(0xE2, 0xDB, 0xCC)
CARD = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "微软雅黑"
MONO = "Consolas"

W, H = 13.333, 7.5
M = 0.85
CW = W - 2 * M

prs = Presentation()
prs.slide_width = Inches(W)
prs.slide_height = Inches(H)
BLANK = prs.slide_layouts[6]

_n = {"page": 0}


# ------------------------------------------------------------------ 基础
def new_slide(bg=None):
    s = prs.slides.add_slide(BLANK)
    if bg is not None:
        f = s.background.fill
        f.solid()
        f.fore_color.rgb = bg
    _n["page"] += 1
    return s


def rect(s, x, y, w, h, fill=None, line=None, lw=1.0, radius=None, shape=None):
    if shape is None:
        shape = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    sp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    # 去掉主题样式引用，避免渲染器给每个形状加投影
    style = sp._element.find(qn("p:style"))
    if style is not None:
        sp._element.remove(style)
    if radius and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            sp.adjustments[0] = min(0.5, radius / min(w, h))
        except Exception:
            pass
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(lw)
    sp.shadow.inherit = False
    tf = sp.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return sp


def text(s, x, y, w, h, content, size=14, bold=False, color=GRAY, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, font=FONT, spacing=1.25, space_after=0, spc=None):
    box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = content.split("\n") if isinstance(content, str) else content
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.name = font
        r.font.color.rgb = color
        rPr = r._r.get_or_add_rPr()
        rPr.set("altLang", "zh-CN")
        if spc:
            rPr.set("spc", str(int(spc * 100)))
        # 中文字体
        from pptx.oxml.ns import qn
        ea = rPr.find(qn("a:ea"))
        if ea is None:
            ea = rPr.makeelement(qn("a:ea"), {})
            rPr.append(ea)
        ea.set("typeface", FONT)
    return box


def pic(s, path, x, y, w=None, h=None):
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    return s.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def pic_fit(s, path, bx, by, bw, bh):
    """在给定框内等比放置，返回实际 (x, y, w, h)。"""
    from PIL import Image
    iw, ih = Image.open(path).size
    r = iw / ih
    if bw / bh > r:
        hh = bh
        ww = bh * r
    else:
        ww = bw
        hh = bw / r
    return pic(s, path, bx + (bw - ww) / 2, by + (bh - hh) / 2, w=ww)


def hair(s, x, y, w, color=HAIR, lw=0.75):
    ln = s.shapes.add_connector(1, Inches(x), Inches(y), Inches(x + w), Inches(y))
    ln.line.color.rgb = color
    ln.line.width = Pt(lw)
    return ln


def frame(s, kicker, title, sub=None, dark=False):
    """统一的页眉与页脚。"""
    tcol = WHITE if dark else INK
    scol = RGBColor(0xC9, 0xD6, 0xE2) if dark else GRAY
    accent = ACCENT

    text(s, M, 0.46, 8, 0.26, kicker, 10.5, True, accent, spc=1.2)
    text(s, M, 0.76, CW, 0.62, title, 26, True, tcol, spacing=1.1)
    if sub:
        text(s, M, 1.44, CW * 0.86, 0.34, sub, 13.5, False, scol, spacing=1.3)

    if not dark:
        hair(s, M, 6.94, CW, HAIR, 0.75)
        text(s, M, 7.02, 6, 0.24, "物归 · 校园失物智能招领平台", 9, False, MUTED)
    text(s, W - M - 1.2, 7.02 if not dark else 6.98, 1.2, 0.24,
         f"{_n['page']:02d}", 9, True, MUTED if not dark else RGBColor(0x8C, 0xA0, 0xB4),
         align=PP_ALIGN.RIGHT)


def card(s, x, y, w, h, fill=CARD, line=HAIR, radius=0.09):
    return rect(s, x, y, w, h, fill=fill, line=line, lw=0.9, radius=radius)


def badge(s, x, y, txt, fg=WHITE, bg=ACCENT, size=9.5, padx=0.13, h=0.26):
    wpx = 0.62 + len(txt) * 0.11 if txt.isascii() else 0.34 + len(txt) * 0.155
    rect(s, x, y, wpx, h, fill=bg, radius=h / 2)
    text(s, x, y + 0.02, wpx, h, txt, size, True, fg, PP_ALIGN.CENTER)
    return wpx


# ------------------------------------------------------------------ 01 封面
def s_cover():
    s = new_slide(CREAM)
    text(s, M, 0.62, 9, 0.3, "杭州电子科技大学　·　第二届 AIGC 应用创新大赛", 11.5, True, ACCENT, spc=0.8)

    text(s, M - 0.06, 1.62, 6.4, 1.5, "物　归", 78, True, INK, spacing=1.0)
    text(s, M, 3.28, 7.2, 0.5, "校园失物智能招领平台", 24, False, GRAY)
    text(s, M, 3.86, 7.2, 0.3, "GUIWU · A CAMPUS LOST & FOUND PLATFORM", 9.5, True, MUTED, spc=1.6)

    rect(s, M, 4.5, 1.1, 0.045, fill=ACCENT)

    text(s, M, 4.78, 6.9, 0.9, "拍一张照片，让失物自己找到主人。", 19, False, INK, spacing=1.35)
    text(s, M, 5.62, 6.6, 0.8,
         "多模态识别完成入库，语义匹配给出候选与理由，\n特征问答完成认领核验——一个从输入到交接的完整闭环。",
         11.5, False, GRAY, spacing=1.55)

    text(s, M, 6.72, 5.4, 0.3, "赛题一　AI 辅助开发 · 创意产品原型", 11, True, INK)
    text(s, M, 7.02, 6.4, 0.26, "团队 5 人 · 软件工程专业　｜　指导教师：【待填】", 9.5, False, MUTED)

    ph = pic(s, "figs/fig6_find.png", 9.05, 0.72, h=6.1)
    _ = ph


# ------------------------------------------------------------------ 02 问题
def s_problem():
    s = new_slide()
    frame(s, "01　问题", "丢一件东西，要失败三次",
          "我们访谈与观察到的三类人，卡在三个不同的位置上。")

    cols = [
        ("失主", "“在群里发了一条，两小时后被作业刷没了。”",
         "沉默成本最高的时刻，没有任何回应。", "01"),
        ("拾得者", "“卡面有姓名学号，发群里等于公开别人信息。”",
         "怕担责、怕麻烦，干脆不交。", "02"),
        ("管理员", "“登记本只写‘雨伞一把’，学期末无人认领。”",
         "收了四十件，认领的不到五件。", "03"),
    ]
    cw = (CW - 0.5) / 3
    for i, (role, quote, cost, num) in enumerate(cols):
        x = M + i * (cw + 0.25)
        card(s, x, 1.98, cw, 3.28)
        text(s, x + 0.34, 2.2, cw - 0.68, 0.28, num, 10, True, ACCENT, spc=1.2)
        text(s, x + 0.34, 2.46, cw - 0.68, 0.4, role, 17, True, INK)
        text(s, x + 0.34, 2.98, cw - 0.68, 1.3, quote, 13, False, GRAY, spacing=1.55)
        hair(s, x + 0.34, 4.26, cw - 0.68, HAIR, 0.75)
        text(s, x + 0.34, 4.4, cw - 0.68, 0.7, cost, 11.5, False, TEAL, spacing=1.4)

    rect(s, M, 5.56, CW, 1.04, fill=CREAM, radius=0.08)
    text(s, M + 0.36, 5.72, CW - 0.72, 0.7,
         "三个人，三种失败，但底层原因只有一个：失物信息始终以非结构化的形态存在，"
         "所以既不能被检索，也不能被匹配，更不能被追溯。",
         13, False, INK, spacing=1.5)


# ------------------------------------------------------------------ 03 现有方案
def s_alternatives():
    s = new_slide()
    frame(s, "01　问题", "校园里不缺发布渠道",
          "我们逐一评估了同学最常用的四种方式。")

    cols = [("方案", 3.1), ("能做对什么", 3.5), ("局限", 4.55)]
    x0 = M
    y = 1.94
    # 表头
    cx = x0
    for name, ww in cols:
        text(s, cx + 0.12, y, ww, 0.3, name, 10.5, True, MUTED, spc=0.8)
        cx += ww
    hair(s, M, y + 0.36, CW, INK, 1.0)

    rows = [
        ("班级群 / 表白墙", "零成本、覆盖广、有人看", "信息流式排列，无检索、无结构，很快沉底，还暴露个人信息"),
        ("二手交易平台", "有成熟的发布与搜索", "定位是交易而非招领，没有认领核验，身份与场景都不匹配"),
        ("保卫处 / 宿管登记", "有权威性、有实物保管", "只覆盖“被上交”的物品，登记负担重，学生触达率低"),
        ("在线表单 / 问卷", "能把信息收集得比较齐", "只收集不匹配，最终仍要人工逐条比对，反而增加整理成本"),
    ]
    rh = 0.8
    for i, r in enumerate(rows):
        ry = y + 0.5 + i * rh
        if i % 2 == 1:
            rect(s, M, ry - 0.02, CW, rh - 0.04, fill=PAPER)
        cx = x0
        for j, (val, (name, ww)) in enumerate(zip(r, cols)):
            text(s, cx + 0.12, ry + 0.2, ww - 0.3, 0.5, val,
                 12.5 if j else 13, j == 0, INK if j == 0 else GRAY, spacing=1.4)
            cx += ww
        hair(s, M, ry + rh - 0.06, CW, HAIR, 0.6)

    rect(s, M, 5.88, CW, 0.72, fill=INK, radius=0.06)
    text(s, M + 0.34, 6.04, CW - 0.68, 0.42,
         "缺的不是“发布渠道”，而是把一段口语、一张照片转成“可被匹配的结构”的那一步。",
         13.5, True, WHITE, spacing=1.2)


# ------------------------------------------------------------------ 04 洞察
def s_insight():
    s = new_slide(CREAM)
    text(s, M, 0.46, 8, 0.26, "02　洞察", 10.5, True, ACCENT, spc=1.2)

    text(s, M, 1.5, CW - 0.4, 1.9,
         "同一件物品，在失主口中是模糊记忆，\n在拾得者手里是精确观察。",
         35, True, INK, spacing=1.35)

    text(s, M, 3.62, CW * 0.78, 0.9,
         "匹配的本质，就是把这两条投影对齐。而“读懂照片、听懂口语、说清理由”，恰好是大模型最擅长的三件事。",
         15, False, GRAY, spacing=1.6)

    tags = [("读得懂照片", "多模态识别"), ("听得懂口语", "查询改写"), ("说得清理由", "可解释精排")]
    tw = 2.55
    for i, (a, b) in enumerate(tags):
        x = M + i * (tw + 0.28)
        card(s, x, 4.82, tw, 1.06, fill=WHITE)
        text(s, x + 0.28, 5.0, tw - 0.5, 0.3, a, 13.5, True, INK)
        text(s, x + 0.28, 5.34, tw - 0.5, 0.3, b, 10.5, False, MUTED, spc=0.6)

    text(s, W - M - 2.2, 7.02, 2.2, 0.24, f"{_n['page']:02d}", 9, True, MUTED, PP_ALIGN.RIGHT)


# ------------------------------------------------------------------ 05 定位
def s_positioning():
    s = new_slide()
    frame(s, "02　洞察", "所以它不是失物墙，是匹配引擎")

    text(s, M, 1.9, 5.5, 1.5,
         "发布只是副产品。\n真正的价值，发生在照片变成字段、\n口述变成条件的那一瞬间。",
         20, True, INK, spacing=1.55)

    text(s, M, 3.72, 5.4, 1.9,
         "这决定了我们的功能优先级：宁可少做一个页面，\n也要把“识别得准”和“匹配得对”做出来。\n"
         "因为一旦这两步错了，后面所有页面都是装饰。",
         12.5, False, GRAY, spacing=1.7)

    items = [
        ("01", "拾得者零负担", "能拍照就不填表，必填项压到三个：时间、地点、隐藏特征。"),
        ("02", "匹配必须可解释", "每条候选都说清“为什么是它”“哪里对不上”，让人敢信。"),
        ("03", "隐私默认最小", "姓名学号默认不出现，联系方式不落库，核验通过才给凭证。"),
    ]
    for i, (n, t, d) in enumerate(items):
        y = 1.92 + i * 1.52
        text(s, 7.05, y + 0.04, 0.5, 0.3, n, 10, True, ACCENT, spc=1.0)
        text(s, 7.55, y, 4.95, 0.34, t, 15, True, INK)
        text(s, 7.55, y + 0.4, 4.9, 0.7, d, 11.5, False, GRAY, spacing=1.55)
        if i < 2:
            hair(s, 7.05, y + 1.24, 5.45, HAIR, 0.75)


# ------------------------------------------------------------------ 06 闭环
def s_loop():
    s = new_slide()
    frame(s, "03　方案", "六步闭环：从一张照片到一次交接",
          "第 2 步和第 5 步，是 AIGC 不可替代的位置——一次替掉了填表，一次替掉了报学号。")
    pic_fit(s, "figs/fig1_loop_nt.png", M - 0.15, 1.92, CW + 0.3, 4.42)

    rect(s, M, 6.44, CW, 0.44, fill=CREAM, radius=0.05)
    text(s, M + 0.24, 6.53, CW - 0.5, 0.3,
         "整条链路只要求拾得者做三个动作：拍一张、选三个下拉、确认发布。",
         11, False, INK)


# ------------------------------------------------------------------ 07 功能
def s_features():
    s = new_slide()
    frame(s, "03　方案", "功能地图：先做通，再做好",
          "P0 是三天内必须跑通的闭环，也是演示视频的主线；P2 明确写进 V1.1。")

    mods = [
        ("拾得入库", "P0", ["拍照识别", "字段修正", "隐私开关"]),
        ("智能寻回", "P0", ["口语输入", "Top-3 与理由", "条件筛选"]),
        ("核验认领", "P0", ["隐藏特征", "三题核验", "一次性认领码"]),
        ("核销归档", "P1", ["扫码核销", "状态流转", "操作留痕"]),
        ("运营洞察", "P2", ["失物热力图", "滞留预警", "月度报告"]),
    ]
    cw = (CW - 0.44) / 5
    for i, (name, pr, feats) in enumerate(mods):
        x = M + i * (cw + 0.11)
        card(s, x, 1.98, cw, 2.96, fill=WHITE if pr != "P2" else PAPER,
             line=HAIR if pr != "P2" else RGBColor(0xEC, 0xE6, 0xD8))
        text(s, x + 0.24, 2.18, cw - 0.4, 0.32, name, 14.5, True, INK if pr != "P2" else MUTED)
        badge(s, x + 0.24, 2.6, pr, bg=ACCENT if pr == "P0" else (TEAL if pr == "P1" else RGBColor(0xD8, 0xD2, 0xC4)),
              size=8.5, h=0.23, padx=0.1)
        for j, f in enumerate(feats):
            text(s, x + 0.24, 3.1 + j * 0.5, cw - 0.42, 0.3, "· " + f,
                 10.5, False, GRAY if pr != "P2" else MUTED, spacing=1.3)

    text(s, M, 5.24, CW, 0.34, "被砍掉的两类功能，以及为什么", 13, True, INK)
    outs = [
        ("失物热力图 / 滞留预警", "需要长期运营数据才成立，三天内做不出可信结论。"),
        ("校园统一身份认证", "对接需要审批流程，用“学号 + 认领码”先替代，避免拖垮主线。"),
    ]
    for i, (t, d) in enumerate(outs):
        x = M + i * (CW / 2 + 0.1)
        text(s, x, 5.66, CW / 2 - 0.3, 0.28, t, 11.5, True, TEAL)
        text(s, x, 5.98, CW / 2 - 0.3, 0.5, d, 10.5, False, MUTED, spacing=1.45)


# ------------------------------------------------------------------ 08 界面
def s_ui():
    s = new_slide()
    frame(s, "03　方案", "30 秒发布，6 秒找回",
          "拾得侧只有一个主按钮；失主侧先看理由，再看分数。")
    pic_fit(s, "figs/fig5_two.png", M - 0.1, 1.86, 7.5, 4.9)

    notes = [
        ("首屏只有拍照", "识别结果折叠成六个字段，\n改不了的东西不让人改。"),
        ("理由放在分数之上", "先帮失主做判断，\n再用相似度排序。"),
        ("核验通过才出现凭证", "凭证带 24 小时倒计时，\n并写明去哪里、找谁领。"),
    ]
    for i, (t, d) in enumerate(notes):
        y = 2.02 + i * 1.42
        rect(s, 8.42, y + 0.06, 0.06, 0.9, fill=ACCENT if i == 0 else HAIR)
        text(s, 8.66, y, 4.0, 0.3, t, 13, True, INK)
        text(s, 8.66, y + 0.36, 3.95, 0.6, d, 10.5, False, GRAY, spacing=1.5)


# ------------------------------------------------------------------ 09 架构
def s_arch():
    s = new_slide()
    frame(s, "04　技术", "架构：把模型收进“能力层”",
          "业务代码不直接依赖任何一家模型——换模型只改网关里的一行配置。")
    pic_fit(s, "figs/fig2_arch_nt.png", M - 0.2, 1.9, CW + 0.4, 4.55)
    text(s, M, 6.52, CW, 0.3,
         "三天冲刺里，这是最划算的工程决策：不必为了换一个模型去翻遍业务代码。",
         10.5, False, MUTED)


# ------------------------------------------------------------------ 10 能力组合
def s_capability():
    s = new_slide()
    frame(s, "04　技术", "不训练模型，只编排模型",
          "本作品没有训练任何模型，全部能力来自对现有模型的选择、约束与组合。")

    heads = [("能力", 2.5), ("承担模型", 2.5), ("在流程中的作用", 6.6)]
    cx = M
    for name, ww in heads:
        text(s, cx + 0.1, 1.92, ww, 0.28, name, 10, True, MUTED, spc=0.8)
        cx += ww
    hair(s, M, 2.26, CW, INK, 1.0)

    rows = [
        ("多模态识别", "千问-VL", "把照片转成类别、品牌、颜色与显著特征"),
        ("结构化抽取", "千问-VL / Qwen-Max", "输出受 Schema 约束的 JSON，保证下游可检索"),
        ("查询改写", "Qwen-Max", "把“昨天下午”折算成时间窗，把口语变成条件"),
        ("相关性重排", "Qwen-Max", "逐条判分并给出理由、指出冲突字段"),
        ("核验问答", "Qwen-Max", "生成三道开放题，并判断答案是否语义等价"),
        ("隐私脱敏", "千问-VL + 正则", "在入库前完成卡面信息的识别与掩码"),
    ]
    rh = 0.66
    for i, r in enumerate(rows):
        ry = 2.36 + i * rh
        if i % 2 == 1:
            rect(s, M, ry - 0.03, CW, rh - 0.02, fill=PAPER)
        cx = M
        for j, (val, (name, ww)) in enumerate(zip(r, heads)):
            text(s, cx + 0.1, ry + 0.14, ww - 0.2, 0.34, val,
                 11.5 if j != 0 else 12, j == 0, INK if j == 0 else GRAY, spacing=1.2)
            cx += ww

    rect(s, M, 6.36, CW, 0.5, fill=CREAM, radius=0.05)
    text(s, M + 0.24, 6.46, CW - 0.5, 0.3,
         "重点不是写多复杂的代码，而是清楚每一处该让模型做什么、不该让它做什么。", 10.5, False, INK)


# ------------------------------------------------------------------ 11 关键技术1
def s_k1():
    s = new_slide()
    frame(s, "04　技术", "关键 ①　拍照即入库：受约束的结构化抽取")

    text(s, M, 1.86, 5.0, 0.32, "三条硬约束", 13, True, INK)
    rules = [
        ("只写看得见的", "看不见的字段一律 unknown，禁止根据常识推断。"),
        ("宁可留空", "早期版本把所有耳机都补成 Apple，检索时凭空多出一批错误候选。"),
        ("过不了校验就重试", "Pydantic 校验失败时带上错误信息重试一次，仍失败则降级手填。"),
    ]
    for i, (t, d) in enumerate(rules):
        y = 2.28 + i * 1.16
        text(s, M, y, 0.4, 0.28, f"0{i+1}", 9.5, True, ACCENT, spc=0.8)
        text(s, M + 0.42, y - 0.02, 4.6, 0.3, t, 12.5, True, INK)
        text(s, M + 0.42, y + 0.34, 4.55, 0.66, d, 10.5, False, GRAY, spacing=1.5)

    # 右侧 JSON
    bx, by, bw, bh = 6.35, 1.86, 6.13, 4.05
    rect(s, bx, by, bw, bh, fill=RGBColor(0xF7, 0xF4, 0xED), line=None, radius=0.08)
    text(s, bx + 0.3, by + 0.18, 4, 0.26, "模型输出（严格 Schema）", 9, True, ACCENT, spc=0.8)
    code = [
        "{",
        '  "subject": "无线耳机",',
        '  "brand": "unknown",',
        '  "color": "白色",',
        '  "features": ["入耳式", "盒面卡通猫贴纸"],',
        '  "sensitive": false,',
        '  "confidence": 0.86',
        "}",
    ]
    text(s, bx + 0.3, by + 0.56, bw - 0.6, 2.6, code, 11.5, False, RGBColor(0x2B, 0x35, 0x3D),
         font=MONO, spacing=1.45)
    hair(s, bx + 0.3, by + 3.22, bw - 0.6, RGBColor(0xDE, 0xD6, 0xC4), 0.75)
    text(s, bx + 0.3, by + 3.38, bw - 0.6, 0.5,
         "品牌在这一张图里确实看不见，所以它是 unknown，而不是“猜一个最像的”。",
         10, False, GRAY, spacing=1.45)

    rect(s, M, 6.28, CW, 0.5, fill=CREAM, radius=0.05)
    text(s, M + 0.24, 6.38, CW - 0.5, 0.3,
         "字段一旦结构化，才谈得上检索——这是后面所有能力的前提。", 10.5, False, INK)


# ------------------------------------------------------------------ 12 关键技术2
def s_k2():
    s = new_slide()
    frame(s, "04　技术", "关键 ②　双通道匹配：给出理由，而不只是分数")

    chans = [
        ("通道 A｜失主怎么找", "「昨天下午在 3 教丢了个白色无线耳机」", ACCENT, RGBColor(0xF8, 0xF2, 0xE8)),
        ("通道 B｜拾得者留下什么", "照片 ＋ 时间、地点、隐藏特征三项", TEAL, RGBColor(0xEF, 0xF5, 0xF3)),
    ]
    bw = (CW - 0.34) / 2
    for i, (lab, txt, col, bg) in enumerate(chans):
        x = M + i * (bw + 0.34)
        rect(s, x, 1.8, bw, 0.98, fill=bg, radius=0.07)
        text(s, x + 0.28, 1.94, bw - 0.5, 0.26, lab, 9.5, True, col, spc=0.8)
        text(s, x + 0.28, 2.22, bw - 0.5, 0.4, txt, 12, True, INK)

    for x in (M + bw / 2, M + bw + 0.34 + bw / 2):
        s.shapes.add_connector(1, Inches(x), Inches(2.82), Inches(x), Inches(2.98)).line.color.rgb = HAIR

    rows = [
        ("改写", "口语 → 结构化条件", "类别 / 颜色 / 地点 / 时间窗；用户没提到的品牌保持开放，避免漏召回"),
        ("召回", "硬过滤 ＋ 双路相似度", "SQL 过滤（在库 · 类别同域 · ±3 天 · 校区）→ 关键词 ∪ 向量 → 去重取 Top-20"),
        ("精排", "大模型交叉核对", "「失主条件 × 候选条目」成对送模型：是否同一件 / 哪些字段冲突 / 一句人话理由"),
    ]
    for i, (tag, t, d) in enumerate(rows):
        y = 3.04 + i * 0.9
        rect(s, M, y, 1.34, 0.74, fill=INK, radius=0.07)
        text(s, M, y + 0.22, 1.34, 0.3, tag, 13, True, WHITE, PP_ALIGN.CENTER)
        text(s, M + 1.56, y + 0.02, 4.3, 0.3, t, 12.5, True, INK)
        text(s, M + 1.56, y + 0.36, CW - 1.6, 0.32, d, 10.5, False, GRAY, spacing=1.3)
        if i < 2:
            s.shapes.add_connector(1, Inches(M + 0.67), Inches(y + 0.75),
                                   Inches(M + 0.67), Inches(y + 0.89)).line.color.rgb = HAIR

    rect(s, M, 5.72, CW, 0.66, fill=INK, radius=0.33)
    text(s, M, 5.9, CW, 0.32, "Top-3 候选　＋　匹配理由　＋　得分　→　失主确认后进入特征核验",
         14, True, WHITE, PP_ALIGN.CENTER)

    text(s, M, 6.52, CW, 0.3,
         "综合分 = 规则分 0.4 + 语义分 0.6；地点或时间冲突直接降权，并在卡片上写明冲突点。",
         10.5, False, MUTED)


# ------------------------------------------------------------------ 13 关键技术3
def s_k3():
    s = new_slide()
    frame(s, "04　技术", "关键 ③　用“答特征”替代“报身份”",
          "传统认领靠报学号后四位，既泄露隐私，也挡不住同班同学冒领。")

    bx, by, bw = M, 1.98, 6.2
    card(s, bx, by, bw, 3.5, fill=PAPER, line=RGBColor(0xE8, 0xE1, 0xD2))
    text(s, bx + 0.32, by + 0.22, bw - 0.6, 0.26, "拾得者留下的隐藏特征", 9, True, MUTED, spc=0.8)
    text(s, bx + 0.32, by + 0.52, bw - 0.6, 0.5, "“耳机盒背面有一张卡通猫贴纸”", 14, True, INK)

    qs = [
        ("Q1", "这张贴纸大概是什么样子的？", "答：好像是张猫咪贴纸，在背面"),
        ("Q2", "耳机盒内还有别的东西吗？", "答：好像有一根备用耳塞"),
        ("Q3", "盒子上有没有明显划痕？", "答：没注意，好像没有"),
    ]
    for i, (n, q, a) in enumerate(qs):
        y = by + 1.12 + i * 0.78
        rect(s, bx + 0.32, y, 0.42, 0.26, fill=INK, radius=0.13)
        text(s, bx + 0.32, y + 0.03, 0.42, 0.24, n, 8.5, True, WHITE, PP_ALIGN.CENTER)
        text(s, bx + 0.86, y - 0.02, bw - 1.2, 0.28, q, 11.5, True, INK)
        text(s, bx + 0.86, y + 0.28, bw - 1.2, 0.26, a, 10, False, GRAY)

    rx = M + bw + 0.42
    rw = W - M - rx
    card(s, rx, by, rw, 3.5)
    text(s, rx + 0.32, by + 0.22, rw - 0.6, 0.26, "判定规则", 9, True, ACCENT, spc=0.8)
    text(s, rx + 0.32, by + 0.6, rw - 0.6, 0.9,
         "答对 ≥ 2 题\n且 综合置信度 ≥ 0.7", 16, True, INK, spacing=1.5)
    text(s, rx + 0.32, by + 1.72, rw - 0.62, 0.5,
         "→ 发放一次性认领码（24 小时有效）", 11.5, True, TEAL)
    text(s, rx + 0.32, by + 2.24, rw - 0.62, 0.5,
         "→ 否则转入人工复核，由管理员线下确认", 11.5, False, GRAY)
    hair(s, rx + 0.32, by + 2.92, rw - 0.64, HAIR, 0.75)
    text(s, rx + 0.32, by + 3.04, rw - 0.62, 0.4,
         "开放题而非是非题，是为了防止逐个试答案。", 9.5, False, MUTED, spacing=1.35)

    rect(s, M, 5.76, CW, 0.62, fill=INK, radius=0.06)
    text(s, M + 0.3, 5.9, CW - 0.6, 0.34,
         "宁可多一次线下确认，也不误放一次冒领——这是把麻烦交给模型、把安全留给用户。",
         12, True, WHITE)


# ------------------------------------------------------------------ 14 关键技术4
def s_k4():
    s = new_slide()
    frame(s, "04　技术", "关键 ④　隐私分级：默认最小可见")

    levels = [
        ("公开", "类别、颜色、地点、时间", TEAL),
        ("认领后可见", "保管点、认领码", INK),
        ("仅管理员", "卡面特征、纠纷记录", MUTED),
    ]
    cw = (CW - 0.52) / 3
    for i, (lv, fields, col) in enumerate(levels):
        x = M + i * (cw + 0.26)
        card(s, x, 1.96, cw, 1.48)
        rect(s, x, 1.96, 0.07, 1.48, fill=col)
        text(s, x + 0.34, 2.16, cw - 0.6, 0.3, lv, 15, True, col)
        text(s, x + 0.34, 2.56, cw - 0.62, 0.7, fields, 11.5, False, GRAY, spacing=1.45)

    text(s, M, 3.72, CW, 0.3, "脱敏前后", 12.5, True, INK)
    pairs = [
        ("姓名　张三", "姓名　张**"),
        ("学号　21051234", "学号　2105****"),
        ("联系电话　13812341234", "不落库，站内信转发"),
    ]
    for i, (a, b) in enumerate(pairs):
        y = 4.14 + i * 0.56
        text(s, M + 0.1, y, 3.2, 0.3, a, 11, False, MUTED)
        text(s, M + 3.5, y, 0.4, 0.3, "→", 11, True, ACCENT)
        text(s, M + 3.96, y, 4.2, 0.3, b, 11, True, INK)

    bx = 7.6
    card(s, bx, 3.66, W - M - bx, 2.5, fill=CREAM, line=CREAM)
    text(s, bx + 0.34, 3.86, 0.6, 0.3, "！", 20, True, ACCENT)
    text(s, bx + 0.78, 3.9, W - M - bx - 1.1, 0.9,
         "这条规则不是设计时想到的，\n是测试时抓包发现的。", 12, True, INK, spacing=1.5)
    text(s, bx + 0.78, 4.92, W - M - bx - 1.1, 0.9,
         "公开接口曾返回过含姓名的条目，后来按 visibility 统一裁剪响应，并补了接口级用例。",
         10, False, GRAY, spacing=1.5)

    rect(s, M, 6.3, CW, 0.48, fill=CREAM, radius=0.05)
    text(s, M + 0.24, 6.4, CW - 0.5, 0.3,
         "隐私不是一句口号，而是三条能落到代码里的规则：默认不展示、按需可见、最小留存。",
         10.5, False, INK)


# ------------------------------------------------------------------ 15 创新点
def s_innovation():
    s = new_slide()
    frame(s, "05　价值", "四个创新点")

    items = [
        ("01", "从“发一条消息”到“建一条数据”",
         "同类作品停在信息发布，我们把照片与口语转成可检索的结构——这一步做成了，后面才有匹配和统计。"),
        ("02", "给理由，而不只是给分数",
         "在失物场景里，判断成本比搜索成本更高。一句“因为类别和地点都对得上”，比把相似度从 0.82 提到 0.86 有用。"),
        ("03", "答特征，而不是报身份",
         "认领核验是同类产品几乎都跳过的一环，因为它麻烦。但恰恰是它，决定了拾得者敢不敢交。"),
        ("04", "从“找回”到“少丢”",
         "失物信息一旦被结构化沉淀，热力图、滞留预警与月度报告才成为可能——这是从服务个体到服务治理的一步。"),
    ]
    cw = (CW - 0.36) / 2
    ch = 1.9
    for i, (n, t, d) in enumerate(items):
        x = M + (i % 2) * (cw + 0.36)
        y = 1.94 + (i // 2) * (ch + 0.26)
        card(s, x, y, cw, ch)
        text(s, x + 0.3, y + 0.18, 0.5, 0.26, n, 9.5, True, ACCENT, spc=1.0)
        text(s, x + 0.3, y + 0.46, cw - 0.6, 0.34, t, 14.5, True, INK)
        text(s, x + 0.3, y + 0.88, cw - 0.62, 0.9, d, 10.8, False, GRAY, spacing=1.5)


# ------------------------------------------------------------------ 16 价值
def s_value():
    s = new_slide()
    frame(s, "05　价值", "谁能用，能用到哪", "核心链路与场景耦合度低：换一套字典，就能换一个地方。")

    cols = [
        ("对学生", "把“发消息等回音”换成“描述即检索”",
         ["失主：从数天缩短到几分钟", "拾得者：从跑两趟到拍一张", "认领：一次问答，不用加好友"]),
        ("对学校", "第一次拥有可统计的失物数据",
         ["楼栋与时段的高频丢失点", "超期未认领的滞留清单", "给保卫处与权益部的处置依据"]),
        ("对同类场景", "换字典即可迁移",
         ["其他高校：替换校区与楼栋", "园区 / 写字楼：替换物品类别", "场馆：替换保管点与流程"]),
    ]
    cw = (CW - 0.5) / 3
    for i, (t, lead, pts) in enumerate(cols):
        x = M + i * (cw + 0.25)
        card(s, x, 1.96, cw, 3.5, fill=WHITE if i < 2 else CREAM,
             line=HAIR if i < 2 else CREAM)
        text(s, x + 0.3, 2.16, cw - 0.6, 0.34, t, 15, True, INK)
        text(s, x + 0.3, 2.6, cw - 0.62, 0.8, lead, 11, False, TEAL, spacing=1.45)
        for j, p in enumerate(pts):
            text(s, x + 0.3, 3.5 + j * 0.56, cw - 0.62, 0.4, "· " + p, 10.5, False, GRAY, spacing=1.4)

    text(s, M, 5.76, CW, 0.34,
         "迁移成本主要在校验规则与提示词上，而不在代码本身——这也是我们把 Prompt 资产化的原因。",
         11.5, False, INK)


# ------------------------------------------------------------------ 17 团队
def s_team():
    s = new_slide()
    frame(s, "06　团队", "五个人，一条链路一个人",
          "按“一条链路一个人”划分，而不是按前后端硬切——每个人都对某个完整功能负责到底。")

    members = [
        ("A", "负责人 / 产品", "需求收敛、流程、答辩主讲"),
        ("B", "前端 · 学生侧", "入库页、寻回页、核验页"),
        ("C", "前端 · 管理端", "列表、核销、状态流转"),
        ("D", "AI 工程师", "Prompt、识别与精排、评测"),
        ("E", "后端 / 测试", "接口、数据库、部署、视频"),
    ]
    rh = 0.7
    for i, (k, role, work) in enumerate(members):
        y = 1.96 + i * rh
        rect(s, M, y, 0.44, 0.44, fill=INK, radius=0.1)
        text(s, M, y + 0.1, 0.44, 0.26, k, 11, True, WHITE, PP_ALIGN.CENTER)
        text(s, M + 0.62, y + 0.06, 2.1, 0.3, role, 12.5, True, INK)
        text(s, M + 2.8, y + 0.08, 3.4, 0.3, work, 11, False, GRAY)

    # 里程碑
    tx = 7.15
    text(s, tx, 1.9, 4.8, 0.3, "里程碑", 12.5, True, INK)
    hair(s, tx + 0.1, 2.62, 4.55, HAIR, 1.2)
    miles = [("第 5—6 周", "选题与验证"), ("第 7—8 周", "设计"), ("第 9—11 周", "开发与联调"),
             ("第 12 周", "材料与提交")]
    for i, (wk, what) in enumerate(miles):
        x = tx + 0.1 + i * (4.55 / 3)
        rect(s, x - 0.07, 2.55, 0.14, 0.14, fill=ACCENT if i == 3 else INK, shape=MSO_SHAPE.OVAL)
        text(s, x - 0.5, 2.82, 1.5, 0.26, wk, 8.5, True, MUTED, spc=0.4)
        text(s, x - 0.5, 3.08, 1.5, 0.26, what, 10, False, GRAY)

    rect(s, tx, 4.24, 4.75, 1.86, fill=CREAM, radius=0.08)
    text(s, tx + 0.28, 4.42, 4.2, 0.28, "提交前三天", 10.5, True, ACCENT, spc=0.8)
    text(s, tx + 0.28, 4.72, 4.2, 1.2,
         "D1 冻结范围、打通入库\nD2 打通寻回与核验\nD3 补材料、录屏、提交",
         10.5, False, INK, spacing=1.65)


# ------------------------------------------------------------------ 18 测试
def s_test():
    s = new_slide()
    frame(s, "06　团队", "三轮迭代，五个坑", "测试不追求覆盖率，而是围绕“会不会在答辩现场翻车”设计。")

    rounds = [
        ("V0.1", "跑通数据流", "用固定 JSON 假装模型返回，先验证前端与数据库。"),
        ("V0.2", "接入真实模型", "发现字段缺失与臆造，加入 Schema 校验与重试。"),
        ("V0.3", "优化匹配", "加入查询改写与成对精排，调权重与阈值。"),
    ]
    for i, (v, t, d) in enumerate(rounds):
        y = 1.98 + i * 1.12
        text(s, M, y, 0.8, 0.28, v, 10.5, True, ACCENT, spc=0.6)
        text(s, M + 0.86, y - 0.02, 4.4, 0.3, t, 12.5, True, INK)
        text(s, M + 0.86, y + 0.32, 4.5, 0.5, d, 10.2, False, GRAY, spacing=1.45)

    text(s, 6.3, 1.9, 5.9, 0.3, "四个指标（目标值）", 12.5, True, INK)
    kpis = [("字段准确率", "≥ 85%"), ("Top-3 命中率", "≥ 80%"),
            ("核验误拒率", "≤ 10%"), ("端到端时延", "≤ 6 秒")]
    cw = (5.9 - 0.24) / 2
    for i, (k, v) in enumerate(kpis):
        x = 6.3 + (i % 2) * (cw + 0.24)
        y = 2.3 + (i // 2) * 1.06
        card(s, x, y, cw, 0.9, fill=PAPER, line=RGBColor(0xEC, 0xE5, 0xD6))
        text(s, x + 0.24, y + 0.14, cw - 0.4, 0.26, k, 9.5, False, MUTED)
        text(s, x + 0.24, y + 0.44, cw - 0.4, 0.34, v, 16, True, INK)

    text(s, 6.3, 4.72, 5.9, 0.3, "五个典型问题", 12.5, True, INK)
    bugs = ["品牌全部填成 Apple → 加 negative 约束",
            "分数扎堆排不出先后 → 改为批量精排",
            "“昨天下午”解析成固定日期 → 注入当前时间",
            "同义表达被判错 → 改为要点比对",
            "公开接口漏做字段裁剪 → 按可见性裁剪"]
    for i, b in enumerate(bugs):
        text(s, 6.3, 5.1 + i * 0.36, 6.0, 0.3, "· " + b, 9.8, False, GRAY, spacing=1.2)


# ------------------------------------------------------------------ 19 复盘
def s_end():
    s = new_slide(CREAM)
    text(s, M, 0.46, 8, 0.26, "07　复盘", 10.5, True, ACCENT, spc=1.2)

    text(s, M, 1.32, CW - 1.0, 0.9, "我们学到的最重要的一件事", 24, True, INK)
    text(s, M, 2.16, CW - 0.6, 1.1, "模型负责起草，人负责确认。", 40, True, INK)

    pts = [
        ("克制比堆功能难", "三天里我们砍掉了热力图、向量库与实名绑定，才让主链路跑通。"),
        ("AI 写的代码要自己读一遍", "它在样板代码上几乎不出错，却会在权限校验上悄悄简化。"),
        ("先跑通闭环，再谈打磨", "评委看到的是一个能用的闭环，而不是五个半成品。"),
    ]
    cw = (CW - 0.5) / 3
    for i, (t, d) in enumerate(pts):
        x = M + i * (cw + 0.25)
        hair(s, x, 3.86, cw - 0.2, ACCENT, 1.5)
        text(s, x, 4.02, cw - 0.2, 0.3, t, 12.5, True, INK)
        text(s, x, 4.36, cw - 0.25, 0.9, d, 10.5, False, GRAY, spacing=1.5)

    hair(s, M, 5.72, CW, RGBColor(0xDD, 0xD5, 0xC4), 0.75)
    text(s, M, 5.9, 7.4, 0.7, "让每一件失物，都能回家。", 26, True, ACCENT)
    text(s, W - M - 4.4, 6.02, 4.4, 0.6,
         "物归 · 校园失物智能招领平台\n杭州电子科技大学　第二届 AIGC 应用创新大赛",
         9.5, False, MUTED, PP_ALIGN.RIGHT, spacing=1.5)
    text(s, W - M - 1.2, 6.98, 1.2, 0.24, f"{_n['page']:02d}", 9, True, MUTED, PP_ALIGN.RIGHT)


def main():
    s_cover()
    s_problem()
    s_alternatives()
    s_insight()
    s_positioning()
    s_loop()
    s_features()
    s_ui()
    s_arch()
    s_capability()
    s_k1()
    s_k2()
    s_k3()
    s_k4()
    s_innovation()
    s_value()
    s_team()
    s_test()
    s_end()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "物归_项目方案.pptx")
    prs.save(out)
    print("saved", out, "slides:", len(prs.slides._sldIdLst))


if __name__ == "__main__":
    main()
