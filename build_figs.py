# -*- coding: utf-8 -*-
"""生成「物归」项目文档与 PPT 所需示意图（Pillow 绘制）。

设计约束：图片按 15cm 宽插入 A4 文档，因此画布 1600px 宽时，
字号需 ≥ 20px（约 6pt）才能在纸面与屏幕上读清。
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

SS = 2
FR = r"C:\Windows\Fonts\msyh.ttc"
FB = r"C:\Windows\Fonts\msyhbd.ttc"

INK = "#17324D"
ACCENT = "#C9622F"
TEAL = "#2E7A72"
LINE = "#DBD4C5"
GRAY = "#4E5A66"
MUTED = "#8B949D"
CREAM = "#F5F0E6"
WHITE = "#FFFFFF"

_fcache = {}


def _font(size, bold=False):
    key = (round(size, 2), bold)
    if key not in _fcache:
        _fcache[key] = ImageFont.truetype(FB if bold else FR, int(round(size * SS)), index=0)
    return _fcache[key]


def _wrap(s, f, maxw, d):
    out = []
    for para in s.split("\n"):
        line = ""
        for ch in para:
            if d.textlength(line + ch, font=f) <= maxw * SS:
                line += ch
            else:
                out.append(line)
                line = ch
        out.append(line)
    return out


class Canvas:
    def __init__(self, w, h, bg=WHITE):
        self.W, self.H = w, h
        mode = "RGBA" if isinstance(bg, tuple) and len(bg) == 4 else "RGB"
        self.im = Image.new(mode, (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.im)

    def box(self, x, y, w, h, r=14, fill=WHITE, outline=LINE, ow=2, shadow=False):
        if shadow:
            self.d.rounded_rectangle(
                [x * SS, (y + 6) * SS, (x + w) * SS, (y + h + 6) * SS],
                radius=r * SS, fill="#E9E2D4")
        self.d.rounded_rectangle(
            [x * SS, y * SS, (x + w) * SS, (y + h) * SS],
            radius=r * SS, fill=fill, outline=outline, width=int(ow * SS))

    def line(self, p1, p2, color=INK, w=2):
        self.d.line([p1[0] * SS, p1[1] * SS, p2[0] * SS, p2[1] * SS],
                    fill=color, width=int(w * SS))

    def dash(self, p1, p2, color=LINE, w=2, on=8, off=6):
        x1, y1 = p1
        x2, y2 = p2
        dist = math.hypot(x2 - x1, y2 - y1)
        if dist == 0:
            return
        ux, uy = (x2 - x1) / dist, (y2 - y1) / dist
        t = 0.0
        while t < dist:
            e = min(t + on, dist)
            self.line((x1 + ux * t, y1 + uy * t), (x1 + ux * e, y1 + uy * e), color, w)
            t = e + off

    def arrow(self, p1, p2, color=INK, w=2.5, head=10):
        x1, y1 = p1
        x2, y2 = p2
        ang = math.atan2(y2 - y1, x2 - x1)
        bx, by = x2 - math.cos(ang) * head, y2 - math.sin(ang) * head
        self.line((x1, y1), (bx, by), color, w)
        left = (bx - math.cos(ang - 0.45) * head, by - math.sin(ang - 0.45) * head)
        right = (bx - math.cos(ang + 0.45) * head, by - math.sin(ang + 0.45) * head)
        self.d.polygon([(x2 * SS, y2 * SS), (left[0] * SS, left[1] * SS),
                        (right[0] * SS, right[1] * SS)], fill=color)

    def circle(self, cx, cy, r, fill=INK, outline=None, ow=0):
        self.d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS],
                       fill=fill, outline=outline, width=int(ow * SS))

    def text(self, x, y, s, size=16, color=GRAY, bold=False, maxw=None,
             align="left", lh=1.5):
        f = _font(size, bold)
        lines = _wrap(s, f, maxw, self.d) if maxw else s.split("\n")
        anchor = {"left": "la", "center": "ma", "right": "ra"}[align]
        yy = y
        for ln in lines:
            self.d.text((x * SS, yy * SS), ln, font=f, fill=color, anchor=anchor)
            yy += size * lh
        return yy - y

    def pill(self, x, y, s, size=12, fg=INK, bg="#EFE9DC", padx=12, h=26):
        f = _font(size, False)
        w = self.d.textlength(s, font=f) / SS + padx * 2
        self.d.rounded_rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS],
                                 radius=h / 2 * SS, fill=bg)
        self.d.text(((x + w / 2) * SS, (y + h / 2) * SS), s, font=f, fill=fg, anchor="mm")
        return w

    def save(self, path):
        self.im.resize((self.W * 2, self.H * 2), Image.LANCZOS).save(path)


OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs")
os.makedirs(OUT, exist_ok=True)


# ------------------------------------------------------------------ 图1 核心闭环
def fig_loop():
    c = Canvas(1600, 790)
    c.text(70, 14, "「物归」核心业务闭环", 28, INK, bold=True)
    w, h = 440, 190
    xs = [70, 580, 1090]
    y1, y2 = 76, 380
    steps = [
        (1, "拍照即入库", "拾得者只拍一张照片，不用填表。AI 识别类别、品牌、颜色与显著特征"),
        (2, "结构化与脱敏", "输出统一 JSON 字段，自动遮蔽卡面姓名与学号，按隐私等级决定公开范围"),
        (3, "一句话寻回", "失主用日常口语描述，系统解析出类别、地点、时间窗与特征词"),
        (4, "匹配与解释", "粗筛候选后由大模型交叉核对，输出 Top-3 与逐条匹配理由"),
        (5, "特征核验", "依据拾得者留下的隐藏特征生成 3 道问题，答对才发认领码"),
        (6, "认领完成", "管理员核销认领码并归档，物品状态与全过程可追溯"),
    ]
    pos = {1: (xs[0], y1), 2: (xs[1], y1), 3: (xs[2], y1),
           4: (xs[2], y2), 5: (xs[1], y2), 6: (xs[0], y2)}
    for n, title, desc in steps:
        x, y = pos[n]
        c.box(x, y, w, h, r=18, shadow=True)
        c.circle(x + 38, y + 38, 21, fill=INK if n <= 3 else TEAL)
        c.text(x + 38, y + 38, str(n), 21, WHITE, bold=True, align="center")
        c.text(x + 74, y + 22, title, 27, INK, bold=True)
        c.text(x + 26, y + 84, desc, 19, GRAY, maxw=w - 52, lh=1.62)

    c.arrow((510, 171), (572, 171), ACCENT, 3)
    c.arrow((1020, 171), (1082, 171), ACCENT, 3)
    c.arrow((1310, 268), (1310, 372), ACCENT, 3)
    c.arrow((1082, 475), (1028, 475), ACCENT, 3)
    c.arrow((572, 475), (518, 475), ACCENT, 3)

    c.box(70, 612, 1460, 118, r=16, fill=CREAM, outline=CREAM, ow=1)
    c.text(96, 630, "运营反哺（V1.1）", 19, ACCENT, bold=True)
    for i, s in enumerate(["失物热力图：哪个楼栋、哪个时段最易丢",
                           "滞留预警：超 14 天未认领自动提醒",
                           "月度报告：给保卫处与权益部的处置依据"]):
        c.text(96 + i * 470, 666, "· " + s, 18, GRAY, maxw=440)
    c.dash((290, 572), (290, 610), LINE, 2)

    c.save(os.path.join(OUT, "fig1_loop.png"))


# ------------------------------------------------------------------ 图2 系统架构
def fig_arch():
    c = Canvas(1600, 1000)
    c.text(60, 12, "系统总体架构", 28, INK, bold=True)

    layers = [
        ("用户层", 78, [("学生端 H5", 1), ("管理端 Web", 1), ("消息通知", 1)], 3, 24, WHITE),
        ("应用层", 288, [("拾得入库", 1), ("智能寻回", 1), ("核验认领", 1), ("核销归档", 1)], 4, 24, WHITE),
        ("AI 能力层", 498, [("多模态识别", 1), ("结构化抽取", 1), ("查询改写", 1),
                            ("精排与解释", 1), ("核验问答", 1), ("隐私脱敏", 1)], 6, 22, "#F8F2E8"),
        ("数据层", 708, [("物品库", 1), ("认领库", 1), ("用户与权限", 1), ("审计日志", 1)], 4, 24, WHITE),
    ]
    bh = 112
    for name, y, items, n, fs, fill in layers:
        c.text(60, y + 44, name, 25, INK, bold=True)
        bw = {3: 420, 4: 317, 6: 205}[n]
        gap = (1330 - bw * n) / (n - 1) if n > 1 else 0
        for i, (t, _) in enumerate(items):
            x = 210 + i * (bw + gap)
            c.box(x, y, bw, bh, r=14, fill=fill)
            c.text(x + bw / 2, y + bh / 2 - fs * 0.62, t, fs, INK, bold=True,
                   align="center", maxw=bw - 16)

    for y in (78, 288, 498):
        for x in (430, 810, 1190):
            c.arrow((x, y + 158), (x, y + 114), "#AEB9C2", 2.2, head=9)
            c.arrow((x, y + 158), (x, y + 202), "#AEB9C2", 2.2, head=9)

    c.line((60, 890), (1540, 890), LINE, 1.5)
    c.text(60, 906, "模型服务　通义千问-VL ｜ text-embedding-v4 ｜ Qwen-Max",
           18, GRAY, maxw=700)
    c.text(1540, 906, "安全　JWT 鉴权 · 字段级脱敏 · 操作审计 · 数据最小化留存",
           18, GRAY, maxw=740, align="right")
    c.save(os.path.join(OUT, "fig2_arch.png"))


# ------------------------------------------------------------------ 图3 匹配链路
def fig_match():
    c = Canvas(1600, 990)
    c.text(70, 12, "双通道匹配：从口语描述到可解释候选", 28, INK, bold=True)

    c.box(70, 76, 680, 132, r=16, fill="#F8F2E8")
    c.text(96, 94, "通道 A｜失主怎么找", 18, ACCENT, bold=True)
    c.text(96, 128, "「昨天下午在 3 教丢了个白色无线耳机」", 20, INK, maxw=630)

    c.box(850, 76, 680, 132, r=16, fill="#EFF5F3")
    c.text(876, 94, "通道 B｜拾得者留下什么", 18, TEAL, bold=True)
    c.text(876, 128, "照片 ＋ 时间、地点、隐藏特征三项", 20, INK, maxw=630)

    c.arrow((410, 212), (410, 250), INK, 2.5)
    c.arrow((1190, 212), (1190, 250), INK, 2.5)

    c.box(70, 254, 680, 152, r=16)
    c.text(96, 274, "查询改写：口语 → 结构化条件", 21, INK, bold=True)
    c.text(96, 310, "类别=耳机　颜色=白　地点=3 教　时间=近 2 天\n品牌未提及 → 保持开放，避免漏召回",
           19, GRAY, maxw=630, lh=1.55)

    c.box(850, 254, 680, 152, r=16)
    c.text(876, 274, "多模态结构化：图片 → 字段", 21, INK, bold=True)
    c.text(876, 310, "类别=无线耳机　品牌=Apple　颜色=白\n特征=入耳式、盒面卡通猫贴纸",
           19, GRAY, maxw=630, lh=1.55)

    c.arrow((410, 410), (410, 448), INK, 2.5)
    c.arrow((1190, 410), (1190, 448), INK, 2.5)

    c.box(70, 452, 1460, 142, r=16, fill=CREAM, outline=CREAM)
    c.text(96, 472, "召回层｜硬条件过滤 ＋ 双路相似度", 21, INK, bold=True)
    c.text(96, 510, "SQL 过滤：在库 ∧ 类别同域 ∧ 时间窗 ±3 天 ∧ 校区匹配　→　关键词 ∪ 向量相似度　→　去重取 Top-20",
           19, GRAY, maxw=1400, lh=1.55)

    c.arrow((800, 598), (800, 636), INK, 2.5)

    c.box(70, 640, 1460, 142, r=16)
    c.text(96, 660, "精排层｜大模型交叉核对，输出理由", 21, INK, bold=True)
    c.text(96, 698, "把「失主条件 ＋ 候选条目」成对送入模型：是否同一件、哪些字段冲突、给一句人话理由",
           19, GRAY, maxw=1400, lh=1.55)

    c.arrow((800, 786), (800, 824), ACCENT, 3)
    c.box(390, 828, 820, 122, r=61, fill=INK, outline=INK)
    c.text(800, 856, "Top-3 候选 ＋ 匹配理由 ＋ 相似度", 25, WHITE, bold=True, align="center")
    c.text(800, 898, "失主确认后进入特征核验，不直接暴露拾得者联系方式", 18, "#C9D6E2", align="center")

    c.save(os.path.join(OUT, "fig3_match.png"))


# ------------------------------------------------------------------ 图4 界面设计稿
def phone_frame(c, x, y, w, h, title):
    c.box(x, y, w, h, r=38, fill="#FFFFFF", outline="#C9C2B3", ow=2, shadow=True)
    c.d.rounded_rectangle([(x + 150) * SS, (y + 12) * SS, (x + w - 150) * SS, (y + 26) * SS],
                          radius=7 * SS, fill="#D8D2C4")
    c.text(x + 28, y + 34, "9:41", 12, INK, bold=True)
    c.text(x + w - 48, y + 34, "5G", 11, INK, align="right")
    for i, hh in enumerate((4, 7, 10)):
        c.d.rounded_rectangle([(x + w - 40 + i * 7) * SS, (y + 46 - hh) * SS,
                               (x + w - 36 + i * 7) * SS, (y + 46) * SS],
                              radius=1.5 * SS, fill=INK)
    c.text(x + w / 2, y + 66, title, 21, INK, bold=True, align="center")
    c.line((x + 24, y + 96), (x + w - 24, y + 96), "#EDE7DA", 1.5)


def phone_upload(c, x, y, w, h):
    phone_frame(c, x, y, w, h, "拾得入库")
    c.d.rounded_rectangle([(x + 26) * SS, (y + 112) * SS, (x + w - 26) * SS, (y + 322) * SS],
                          radius=18 * SS, fill="#FAF7F0", outline="#D6CEC0", width=2 * SS)
    cx, cy = x + w / 2, y + 196
    c.d.rounded_rectangle([(cx - 42) * SS, (cy - 26) * SS, (cx + 42) * SS, (cy + 26) * SS],
                          radius=9 * SS, outline=ACCENT, width=3 * SS)
    c.d.ellipse([(cx - 14) * SS, (cy - 14) * SS, (cx + 14) * SS, (cy + 14) * SS],
                outline=ACCENT, width=3 * SS)
    c.text(cx, y + 246, "拍照或选择图片", 15, INK, bold=True, align="center")
    c.text(cx, y + 274, "自动压缩 · 支持 JPG / PNG", 11, MUTED, align="center")
    c.box(x + 26, y + 340, w - 52, 250, r=14, fill="#FFFFFF", outline="#E6DED0")
    c.text(x + 44, y + 356, "AI 识别结果", 14, INK, bold=True)
    c.pill(x + w - 116, y + 354, "可编辑", 10, TEAL, "#E8F1EF", padx=8, h=20)
    rows = [("类别", "无线耳机"), ("品牌", "Apple"), ("颜色", "白色"),
            ("特征", "入耳式 · 盒面贴纸"), ("地点", "3 教 101"), ("时间", "今天 14:20")]
    for i, (k, v) in enumerate(rows):
        ry = y + 386 + i * 32
        c.text(x + 44, ry, k, 12, MUTED)
        c.text(x + 122, ry, v, 12, INK, maxw=w - 160)
    c.box(x + 26, y + 606, w - 52, 56, r=12, fill="#F7F1E7", outline="#F7F1E7", ow=1)
    c.text(x + 44, y + 622, "隐藏卡面姓名与学号", 12, INK)
    c.d.rounded_rectangle([(x + w - 106) * SS, (y + 622) * SS, (x + w - 46) * SS, (y + 648) * SS],
                          radius=13 * SS, fill=TEAL)
    c.circle(x + w - 60, y + 635, 11, fill=WHITE)
    c.d.rounded_rectangle([(x + 26) * SS, (y + 682) * SS, (x + w - 26) * SS, (y + 738) * SS],
                          radius=28 * SS, fill=INK)
    c.text(x + w / 2, y + 700, "发布到失物库", 16, WHITE, bold=True, align="center")


def phone_find(c, x, y, w, h):
    phone_frame(c, x, y, w, h, "智能寻回")
    c.box(x + 26, y + 112, w - 52, 84, r=16, fill="#F3EEE3", outline="#F3EEE3", ow=1)
    c.text(x + 42, y + 128, "昨天下午在 3 教丢了一个白色无线耳机", 12, INK, maxw=w - 100, lh=1.5)
    c.pill(x + w - 82, y + 166, "AI 解析", 10, WHITE, ACCENT, padx=8, h=20)
    chips = ["耳机", "近 2 天", "3 教"]
    cx = x + 26
    for ch in chips:
        cx += c.pill(cx, y + 208, ch, 11, INK, "#EDE7DA", padx=10, h=24) + 8

    def card(cy, pct, title, meta, reason, hot=False):
        c.box(x + 26, cy, w - 52, 200, r=14, fill="#FFFFFF",
              outline=ACCENT if hot else "#E6DED0", ow=2 if hot else 1.5)
        c.pill(x + w - 108, cy + 14, f"匹配 {pct}%", 10, WHITE, TEAL if not hot else ACCENT,
               padx=9, h=21)
        c.text(x + 42, cy + 16, title, 13, INK, bold=True, maxw=w - 160)
        c.text(x + 42, cy + 44, meta, 10, MUTED, maxw=w - 84)
        c.box(x + 42, cy + 72, w - 84, 84, r=10, fill="#FAF7F0", outline="#FAF7F0", ow=1)
        c.text(x + 54, cy + 82, "推荐理由", 10, ACCENT, bold=True)
        c.text(x + 54, cy + 102, reason, 10, GRAY, maxw=w - 108, lh=1.45)
        c.text(x + 42, cy + 168, "申请认领", 11, INK, bold=True)
        c.text(x + w - 42, cy + 168, "→", 13, ACCENT, align="right")

    card(y + 250, "92", "白色无线耳机 · Apple", "3 教 101 · 今天 14:20 · 在库",
         "类别、地点一致，时间相差 2 小时；同为白色入耳式", hot=True)
    card(y + 470, "78", "白色有线耳机", "2 教 305 · 昨天 18:05 · 在库",
         "类别同域、颜色一致，地点不符，建议核对")
    c.text(x + w / 2, y + 700, "没找到？补充特征（贴纸 / 划痕 / 包装）", 11, MUTED, align="center")


def phone_verify(c, x, y, w, h):
    phone_frame(c, x, y, w, h, "特征核验")
    c.text(x + 26, y + 116, "问题 1 / 3", 11, MUTED)
    c.box(x + 26, y + 138, w - 52, 210, r=14, fill="#F7F1E7", outline="#F7F1E7", ow=1)
    c.text(x + 42, y + 154, "拾得者备注：耳机盒背面有一张贴纸", 10, MUTED, maxw=w - 84, lh=1.45)
    c.text(x + 42, y + 202, "这张贴纸大概是什么样子的？", 15, INK, bold=True, maxw=w - 84, lh=1.5)
    c.box(x + 42, y + 262, w - 84, 66, r=10, fill=WHITE, outline="#E0D8C9", ow=1.5)
    c.text(x + 54, y + 274, "好像是张卡通猫的贴纸，贴在盒子背面", 11, INK, maxw=w - 108, lh=1.45)
    c.d.rounded_rectangle([(x + w - 96) * SS, (y + 306) * SS, (x + w - 54) * SS, (y + 330) * SS],
                          radius=12 * SS, fill=INK)
    c.text(x + w - 75, y + 312, "提交", 10, WHITE, align="center")

    c.text(x + 26, y + 372, "问题 2 / 3（待回答）", 11, MUTED)
    c.box(x + 26, y + 394, w - 52, 74, r=12, fill="#FBF9F4", outline="#EDE7DA", ow=1.5)
    c.text(x + 42, y + 412, "耳机盒内还有别的东西吗？", 12, "#9AA3AC", maxw=w - 84)

    c.box(x + 26, y + 492, w - 52, 168, r=14, fill="#EAF2F0", outline="#EAF2F0", ow=1)
    c.text(x + 44, y + 508, "核验通过 · 置信度 0.86", 12, TEAL, bold=True)
    c.text(x + 44, y + 534, "A7K-92F", 30, INK, bold=True)
    c.text(x + 44, y + 586, "24 小时内到 3 教值班室出示认领码", 10, GRAY, maxw=w - 88, lh=1.4)
    c.d.rounded_rectangle([(x + 26) * SS, (y + 686) * SS, (x + w - 26) * SS, (y + 742) * SS],
                          radius=28 * SS, fill=ACCENT)
    c.text(x + w / 2, y + 704, "查看认领凭证", 16, WHITE, bold=True, align="center")


def render_phone(drawer, ss=3):
    global SS, _fcache
    SS = ss
    _fcache.clear()
    c = Canvas(460, 820, bg=(255, 255, 255, 0))
    drawer(c, 20, 20, 420, 780)
    img = c.im
    SS = 2
    _fcache.clear()
    return img


def fig_ui_multi(name, drawers, phone_w, gap=56, margin=60):
    imgs = [render_phone(d) for d in drawers]
    h = phone_w * 820 / 460
    cw = margin * 2 + phone_w * len(imgs) + gap * (len(imgs) - 1)
    ch = margin * 2 + h
    canvas = Image.new("RGBA", (int(cw * 2), int(ch * 2)), (255, 255, 255, 0))
    x = margin
    for im in imgs:
        w2 = int(phone_w * 2)
        h2 = int(im.height * w2 / im.width)
        canvas.paste(im.resize((w2, h2), Image.LANCZOS), (int(x * 2), int(margin * 2)))
        x += phone_w + gap
    canvas.save(os.path.join(OUT, name))


if __name__ == "__main__":
    fig_loop()
    fig_arch()
    fig_match()
    fig_ui_multi("fig4_ui.png", [phone_upload, phone_find, phone_verify], 430, gap=52)
    fig_ui_multi("fig5_two.png", [phone_find, phone_verify], 520, gap=64)
    fig_ui_multi("fig6_find.png", [phone_find], 560)

    # PPT 用：裁掉图内标题，标题交给幻灯片
    for src in ("fig1_loop", "fig2_arch", "fig3_match"):
        im = Image.open(os.path.join(OUT, f"{src}.png"))
        im.crop((0, 112, im.width, im.height)).save(os.path.join(OUT, f"{src}_nt.png"))

    print("done", sorted(os.listdir(OUT)))
