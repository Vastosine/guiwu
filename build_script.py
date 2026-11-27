# -*- coding: utf-8 -*-
"""生成《「物归」演示视频脚本》docx。复用 build_docx 的排版工具。"""
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

import build_docx as bd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "物归_演示视频脚本.docx")

SHOTS = [
    dict(no="01", t="0:00 — 0:08", name="片头",
         visual="黑底，白色大字「物　归」由虚到实，副标题「校园失物智能招领平台」淡入；"
                "右下角小字「杭州电子科技大学 · 第二届 AIGC 应用创新大赛 · 赛题一」。",
         voice="这是物归——一个让失物自己找到主人的校园招领平台。",
         sub="物归 · 校园失物智能招领平台"),
    dict(no="02", t="0:08 — 0:26", name="三个失败",
         visual="三段素材快切，每段约 5 秒：① 班级群消息快速上滑、被新消息顶走；② 值班室失物箱，镜头慢推；"
                "③ 手写登记本特写，只写着「雨伞　一把」。每段右下角标小字「场景还原」。",
         voice="在校园里丢一件东西，通常要失败三次：发在群里的消息，两小时就被刷没了；"
               "捡到的人怕泄露信息，不敢交；值班室的登记本，只写了一句雨伞一把。",
         sub="丢一件东西，要失败三次"),
    dict(no="03", t="0:26 — 0:56", name="方案与闭环",
         visual="切到闭环图（六个步骤）。说到哪一步，哪一步就高亮放大：第 1—2 步亮起（拍照即入库），"
                "第 3—4 步亮起（匹配与理由），第 5 步亮起（特征核验）。图下方浮出「从输入到交接，一个闭环」。",
         voice="物归把这条链路上的三个卡点，分别交给三项能力：拍照即入库，一句话就能找回，"
               "认领之前还要答对三道只有真失主才知道的问题。整个过程，是从输入到交接的一个闭环。",
         sub="拍照即入库 · 一句话寻回 · 答特征认领"),
    dict(no="04", t="0:56 — 1:36", name="拾得入库",
         visual="切到手机视图（375×812）。点「拍照」→ 选一张耳机照片 → 进度条走 1.5 秒 → 六个字段逐个浮现 → "
                "光标把「颜色」从「白」改成「米白」→ 打开「隐藏卡面姓名与学号」开关 → 点「发布」→ "
                "顶部 toast 显示「已入库 · 状态：在库」。",
         voice="先看拾得者这一侧，他只需要做一件事：拍照。模型返回类别、品牌、颜色和特征；"
               "看不见的字段留空，而不是猜一个。确认之后打开隐私开关，卡面上的姓名学号不会出现在公开页面。"
               "点发布，这条记录就进了失物库。",
         sub="看不见的字段留空 · 默认脱敏"),
    dict(no="05", t="1:36 — 2:20", name="失主寻回",
         visual="切到失主端。在输入框逐字打出「昨天下午在3教丢了个白色无线耳机」→ 点「AI 解析」→ "
                "三个 chip 依次弹出（耳机 / 白色 / 3 教）→ 结果卡两张，第一张描边高亮（匹配约 83%）→ "
                "光标移到「推荐理由」区域，文字轻微放大。",
         voice="再看失主。他不选分类、不选时间，只要把当时的情形说一遍。系统把“昨天下午”折算成时间窗，"
               "把“3 教”归一成楼栋，然后在候选里挑出最像的两条。每一条都给理由：第一条类别、颜色、地点都对得上，"
               "时间只差几个小时；第二条地点不符，所以排在后面。",
         sub="一句口语 → 结构化条件 → Top-3 ＋ 理由"),
    dict(no="06", t="2:20 — 2:58", name="特征核验",
         visual="点第一张卡的「申请认领」→ 进入核验页 → 三道题依次出现，都围绕那个细节："
                "最特别的地方 / 靠什么认出它 / 上面有没有贴纸或划痕 → 三题都用口语作答 → 提交 → "
                "通过，认领码弹入（形如 A7K-92F），下方出现 24 小时倒计时。",
         voice="点申请认领，不会直接拿到对方联系方式，而是进入核验。三道题都围绕拾得者留下的那个细节来问——"
               "换三种问法，是想确认你真的见过它，而不是背下了答案。答对两题、置信度过线，"
               "才生成一次性认领码，24 小时有效。",
         sub="用「答特征」替代「报身份」"),
    dict(no="07", t="2:58 — 3:26", name="管理端核销",
         visual="切到管理端列表 → 搜索刚才那个认领码 → 弹窗显示物品与申请人 → 点「确认核销」→ "
                "状态从「在库」变为「已认领」→ 右侧日志多出一条记录。",
         voice="最后一步在管理端。管理员输入认领码，物品状态从在库变成已认领，操作写进日志——"
               "出了纠纷，可以还原每一次状态变更。",
         sub="核销留痕，全程可追溯"),
    dict(no="08", t="3:26 — 3:56", name="反例演示",
         visual="分屏：左侧用全错的答案走一遍核验，红色提示「未通过 · 已记录一次尝试」；"
                "右侧候选卡片上，红字标出「地点不符 · 已降权」。",
         voice="我们也准备了反例。三道全错，系统拒绝，并记一次失败尝试；地点不符的候选会被直接降权，"
               "并在卡片上写明冲突。宁可多一次线下确认，也不误放一次冒领。",
         sub="反例演示：拒绝与降权"),
    dict(no="09", t="3:56 — 4:24", name="技术底座",
         visual="切架构图（静止），「AI 能力层」在解说时高亮；右侧浮出两行 Prompt 片段"
                "（“看不见的字段一律 unknown” / “只输出 JSON”），逐行显示。",
         voice="技术上，这个作品没有训练任何模型，所有能力都收在一层网关里——换模型只改一行配置。"
               "每一条提示词都写清了该做什么、不该做什么：看不见的品牌必须留空，输出必须是 JSON。",
         sub="不训练模型，只编排模型"),
    dict(no="10", t="4:24 — 4:38", name="附录与核查",
         visual="三张文档截图快切：AI 工具使用清单、测试用例表、人工核查记录，每张停留 3 秒，"
                "配箭头指向表题。",
         voice="用了哪些 AI 工具、每一条提示词、每一轮测试和人工核查，都在项目文档的附录里。",
         sub="AI 使用说明见附录 A—D"),
    dict(no="11", t="4:38 — 4:55", name="收尾",
         visual="回到标题页，团队名称与成员（或以合影代替）淡入，一行字「让每一件失物，都能回家」；"
                "最后 1 秒黑场。",
         voice="物归，让每一件失物，都能回家。谢谢。",
         sub="让每一件失物，都能回家"),
]


def title_block(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    bd.set_font(p.add_run("「物归」演示视频脚本"), bd.HEI, 26, True, bd.INK)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    bd.set_font(p.add_run("5 分钟　·　全程录屏 ＋ 解说　·　赛题一：AI 辅助开发 · 创意产品原型"),
                bd.SONG, 11, False, bd.GRAY)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(14)
    bd.set_font(p.add_run("版本 v1.0　｜　2026 年 11 月　｜　对应作品《物归 · 校园失物智能招领平台》"),
                bd.SONG, 9, False, bd.MUTED)
    bd.p_border(p, "bottom", 8, "C9622F", 8)


def h(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    bd.set_font(p.add_run(text), bd.HEI, 13.5, True, bd.INK)


def shot(doc, d):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    bd.set_font(p.add_run(f"镜 {d['no']}　"), bd.HEI, 11, True, bd.ACCENT)
    bd.set_font(p.add_run(f"{d['t']}　"), bd.SONG, 10.5, True, bd.GRAY)
    bd.set_font(p.add_run(d["name"]), bd.HEI, 11.5, True, bd.INK)
    bd.p_border(p, "top", 4, "E2DBCC", 4)

    pv = doc.add_paragraph()
    pv.paragraph_format.space_after = Pt(3)
    pv.paragraph_format.line_spacing = 1.45
    pv.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    bd.set_font(pv.add_run("画面与操作　"), bd.HEI, 9.5, True, bd.TEAL)
    bd.set_font(pv.add_run(d["visual"]), bd.SONG, 10, False, bd.BLACK)

    pn = doc.add_paragraph()
    pn.paragraph_format.left_indent = Cm(0.4)
    pn.paragraph_format.right_indent = Cm(0.2)
    pn.paragraph_format.space_before = Pt(4)
    pn.paragraph_format.space_after = Pt(4)
    pn.paragraph_format.line_spacing = 1.5
    bd.para_shade(pn, "F7F4ED")
    bd.p_border(pn, "left", 14, "C9622F", 8)
    bd.set_font(pn.add_run("解说词　"), bd.HEI, 9.5, True, bd.ACCENT)
    bd.set_font(pn.add_run("「" + d["voice"] + "」"), bd.SONG, 10.5, False, bd.BLACK)

    ps = doc.add_paragraph()
    ps.paragraph_format.space_after = Pt(6)
    bd.set_font(ps.add_run("屏上字幕　"), bd.HEI, 9, True, bd.MUTED)
    bd.set_font(ps.add_run(d["sub"]), bd.SONG, 9.5, False, bd.GRAY)


def build():
    doc = Document()
    bd.setup_styles(doc)

    sec = doc.sections[0]
    sec.page_width = Cm(21)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.8)
    sec.right_margin = Cm(2.6)
    sec.top_margin = Cm(2.4)
    sec.bottom_margin = Cm(2.2)

    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    bd.set_font(fp.add_run("— "), bd.SONG, 9, False, bd.GRAY)
    for r in bd.add_field(fp, " PAGE ", "1"):
        bd.set_font(r, bd.SONG, 9, False, bd.GRAY)
    bd.set_font(fp.add_run(" —"), bd.SONG, 9, False, bd.GRAY)

    title_block(doc)

    h(doc, "一、成片参数")
    bd.table(doc, "表 1　技术参数与硬性要求",
             ["项目", "要求", "说明"],
             [["时长", "不超过 5 分钟（本脚本 4 分 55 秒）", "留 5 秒缓冲，防止导出后超时"],
              ["格式", "MP4（H.264 ＋ AAC）", "通用播放器可直接播放"],
              ["大小", "不超过 100 MB", "1080p、6—8 Mbps 大约落在 60 MB"],
              ["画面", "1920×1080，30 fps，全程录屏", "不得用静态截图拼接充当录屏"],
              ["声音", "48 kHz，解说清晰，BGM 低于人声约 15 dB", "用耳麦，不要用笔记本内置麦克风"],
              ["命名", "物归_演示视频_团队名称.mp4", "与提交平台的命名要求一致"]],
             [2.2, 7.0, 6.0])

    h(doc, "二、节奏与目标")
    bd.body(doc, "五分钟的视频只有一件事要做：让评委相信这个作品是真的。因此节奏上先给问题、再给方案、"
                   "然后用三分之二的时间演示，最后用技术细节收尾。每一段都有明确的“要让对方得到什么”，"
                   "写不出来就删掉。")
    bd.table(doc, "表 2　五段式节奏",
             ["段落", "时间轴", "这一段要让评委得到什么"],
             [["开场", "0:00 — 0:26", "三句话之内知道这是什么、解决谁的什么问题"],
              ["方案", "0:26 — 1:36", "相信这件事有解，而且解法是闭环的"],
              ["演示", "1:36 — 3:26", "看见它真的能跑：入库、寻回、核验三段完整链路"],
              ["亮点", "3:26 — 4:38", "记住技术差异：反例、架构、提示词约束"],
              ["收尾", "4:38 — 4:55", "留下印象，并知道细节在文档附录里"]],
             [2.0, 3.6, 9.0])

    h(doc, "三、分镜脚本")
    bd.body(doc, "下表逐镜给出画面、操作、解说词与字幕。解说词按每分钟 250 字的语速写成，"
                   "可以直接照读；括号外的停顿按标点处理即可，不必额外加“嗯”“那么”。")
    for d in SHOTS:
        shot(doc, d)

    h(doc, "四、录制前十分钟检查清单")
    bd.body(doc, "录屏翻车大多不是因为功能没做好，而是因为环境和数据没准备好。下面八条，录之前逐条打勾。")
    bd.bullets(doc, [
        "浏览器窗口 1440×900 以上、缩放 100%，隐藏书签栏与扩展图标；手机视图固定 375×812。",
        "演示数据预置 8 条失物，其中 2 条与演示描述高度相关（一条 92%、一条 78%），另留 1 条明显无关的做反例。",
        "提前清库：认领码、核验记录、操作日志全部重置，避免出现“该码已被使用”。",
        "关闭系统通知、微信与邮件弹窗；录屏期间手机静音并反扣。",
        "模型调用先预热一次，避免第一次请求十秒冷启动。",
        "先录三十秒空白，回放确认没有电流声、键盘声与风扇声。",
        "关键三段（入库、寻回、核验）各录两遍，剪辑时挑最顺的一条。",
        "把本脚本打印出来放在屏幕旁，不要一边录一边找台词。",
    ])

    h(doc, "五、口播与画面配合")
    bd.bullets(doc, [
        "解说比操作早半拍：先说“我现在拍一张”，再点拍照——观众才知道该看哪里。",
        "每次点击后停一秒，让结果出来再说话；黑屏等待是最伤观感的。",
        "数字只说一次（“6 秒”“24 小时”），重复强调反而显得心虚。",
        "语速控制在每分钟 240—280 字；本脚本按 250 字设计。",
        "不要念界面上的字，要说它意味着什么——“打开隐私开关”要补一句“姓名学号不会出现在公开页面”。",
    ])

    h(doc, "六、剪辑与导出")
    bd.bullets(doc, [
        "片头三秒、片尾三秒；中间只用硬切，不加花哨转场。",
        "字幕只上关键句，每镜一到两条，不整段逐字上。",
        "BGM 选无版权的轻电子或钢琴，音量约 -22 dB，人声保持 -6 dB 左右。",
        "导出参数：H.264 / 1080p / 30 fps / 6—8 Mbps / AAC 192 kbps。",
        "导出后完整播一遍，检查声画同步、字幕错字、结尾是否被截断。",
    ])

    h(doc, "七、常见翻车点")
    bd.table(doc, "表 3　五个高频问题与规避办法",
             ["现象", "原因", "规避办法"],
             [["模型返回慢，出现八秒冷场", "首次调用冷启动、网络抖动", "提前预热；剪辑时在该处加速 2 倍并补一句画外音"],
              ["识别结果不准", "演示照片模糊、反光或有遮挡", "改用清晰的实物照；必要时用已识别的预置条目"],
              ["弹出“该认领码已被使用”", "数据没有重置", "录前清库，固定一个演示账号"],
              ["字幕出现错字", "没有逐句校对", "导出后对照本脚本逐句看一遍"],
              ["成片超过五分钟", "解说拖沓、操作停顿过长", "按本脚本时间轴逐镜卡点，剪辑时用秒表对"]],
             [4.6, 4.6, 6.2])

    h(doc, "八、素材清单")
    bd.body(doc, "开录之前，把下面这些素材备齐，可以省掉一半重录。")
    bd.table(doc, "表 4　录制素材",
             ["素材", "用途", "备注"],
             [["耳机实物 ＋ 充电盒（带贴纸）", "第 4、6 镜的拍摄与核验", "贴纸必须是“只有失主知道”的细节"],
              ["校园卡（已掩码或样卡）", "隐私脱敏的演示", "不要用真实师生的卡面信息"],
              ["班级群消息录屏", "第 2 镜场景还原", "人名与群名打码"],
              ["失物箱 / 登记本照片", "第 2 镜场景还原", "可用摆拍，标注“场景还原”"],
              ["三张文档截图", "第 10 镜", "AI 工具清单、测试用例、人工核查记录"]],
             [5.4, 4.8, 5.2])

    doc.core_properties.title = "「物归」演示视频脚本"
    doc.core_properties.author = "杭州电子科技大学第二届 AIGC 应用创新大赛参赛团队"
    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    build()

