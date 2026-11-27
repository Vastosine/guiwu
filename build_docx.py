# -*- coding: utf-8 -*-
"""把 doc_content 渲染为规范排版的 docx。"""
import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import (WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import doc_content

INK = RGBColor(0x17, 0x32, 0x4D)
ACCENT = RGBColor(0xC9, 0x62, 0x2F)
TEAL = RGBColor(0x2E, 0x7A, 0x72)
GRAY = RGBColor(0x5C, 0x68, 0x73)
MUTED = RGBColor(0x8B, 0x94, 0x9D)
BLACK = RGBColor(0x1E, 0x2A, 0x33)

HEI = "黑体"
SONG = "宋体"
MONO = "Consolas"
LATIN = "Times New Roman"

TEXT_W = 15.4  # 正文可用宽度（cm）

TBLPR_ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
               "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd",
               "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
               "tblCaption", "tblDescription", "tblPrChange"]


def insert_ordered(parent, el, order=TBLPR_ORDER):
    """按 OOXML schema 顺序插入，避免 Word / WPS 忽略乱序元素。"""
    name = el.tag.split("}")[1]
    idx = order.index(name)
    for child in list(parent):
        cn = child.tag.split("}")[1]
        if cn in order and order.index(cn) > idx:
            child.addprevious(el)
            return el
    parent.append(el)
    return el


def drop_children(parent, *names):
    for child in list(parent):
        if child.tag.split("}")[1] in names:
            parent.remove(child)


def set_tbl_borders(tbl, spec):
    """spec: {side: (val, size_eighth_pt, color)}"""
    tblPr = tbl._tbl.tblPr
    drop_children(tblPr, "tblBorders")
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        val, sz, color = spec.get(side, ("nil", 0, "auto"))
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), val)
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    insert_ordered(tblPr, borders)


def set_tbl_cellmar(tbl, top=60, left=110, bottom=60, right=110):
    tblPr = tbl._tbl.tblPr
    drop_children(tblPr, "tblCellMar")
    mar = OxmlElement("w:tblCellMar")
    for side, w in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(w))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    insert_ordered(tblPr, mar)


def set_tbl_width(tbl, cm_total):
    tblPr = tbl._tbl.tblPr
    for child in list(tblPr):
        if child.tag.split("}")[1] == "tblW":
            child.set(qn("w:type"), "dxa")
            child.set(qn("w:w"), str(int(cm_total / 2.54 * 1440)))
            return


# ------------------------------------------------------------------ 基础工具
def set_font(run, cn=SONG, size=12, bold=None, color=None, latin=LATIN):
    run.font.name = latin
    run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), latin)
    rfonts.set(qn("w:hAnsi"), latin)
    rfonts.set(qn("w:eastAsia"), cn)


def shade(element, fill):
    pr = element.get_or_add_tcPr() if element.tag.endswith("tc") else element.get_or_add_pPr()
    old = pr.find(qn("w:shd"))
    if old is not None:
        pr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pr.append(shd)


def para_shade(p, fill):
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pPr.append(shd)


def first_line_chars(p, chars=200):
    pPr = p._p.get_or_add_pPr()
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLineChars"), str(chars))
    if ind.get(qn("w:firstLine")) is None:
        ind.set(qn("w:firstLine"), "480")


def p_border(p, side="bottom", sz=6, color="D9D2C4", space=4):
    pPr = p._p.get_or_add_pPr()
    pBdr = pPr.find(qn("w:pBdr"))
    if pBdr is None:
        pBdr = OxmlElement("w:pBdr")
        pPr.append(pBdr)
    el = OxmlElement(f"w:{side}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color)
    pBdr.append(el)


def add_field(p, instr, placeholder=""):
    run = p.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    run._r.append(fld)

    run2 = p.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    run2._r.append(it)

    run3 = p.add_run()
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    run3._r.append(sep)

    run4 = p.add_run(placeholder)

    run5 = p.add_run()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run5._r.append(end)
    return [run, run2, run3, run4, run5]


# ------------------------------------------------------------------ 样式
def setup_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = LATIN
    normal.font.size = Pt(12)
    normal.font.color.rgb = BLACK
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), SONG)
    pf = normal.paragraph_format
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(3)

    specs = {
        "Heading 1": (16, 20, 12, 1.3),
        "Heading 2": (14, 14, 8, 1.3),
        "Heading 3": (12.5, 12, 6, 1.3),
    }
    for name, (size, before, after, ls) in specs.items():
        st = doc.styles[name]
        st.font.name = LATIN
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = INK
        st.element.rPr.rFonts.set(qn("w:eastAsia"), HEI)
        st.element.rPr.rFonts.set(qn("w:ascii"), LATIN)
        st.element.rPr.rFonts.set(qn("w:hAnsi"), LATIN)
        f = st.paragraph_format
        f.space_before = Pt(before)
        f.space_after = Pt(after)
        f.line_spacing = ls
        f.keep_with_next = True
        f.first_line_indent = Pt(0)
        f.left_indent = Pt(0)

    doc.styles["Heading 1"].paragraph_format.page_break_before = True


# ------------------------------------------------------------------ 内容构件
def body(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_font(p.add_run(text), SONG, 12, color=BLACK)
    first_line_chars(p)
    return p


def bullets(doc, items):
    for it in items:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf = p.paragraph_format
        pf.left_indent = Cm(0.95)
        pf.first_line_indent = Cm(-0.45)
        pf.space_before = Pt(2)
        set_font(p.add_run("·  "), SONG, 12, bold=True, color=ACCENT)
        set_font(p.add_run(it), SONG, 12, color=BLACK)


def caption(doc, text, above=True):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before = Pt(8 if above else 4)
    pf.space_after = Pt(4 if above else 10)
    pf.line_spacing = 1.15
    pf.keep_with_next = bool(above)
    set_font(p.add_run(text), HEI, 9.5, bold=True, color=INK)
    return p


def figure(doc, path, cap, width):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=Cm(width))
    caption(doc, cap, above=False)


def table(doc, cap, headers, rows, widths):
    caption(doc, cap, above=True)
    total = sum(widths)
    scale = TEXT_W / total
    widths = [w * scale for w in widths]

    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, wcm in enumerate(widths):
        t.columns[i].width = Cm(wcm)
    set_tbl_width(t, sum(widths))
    set_tbl_borders(t, {
        "top": ("single", 12, "17324D"),
        "bottom": ("single", 12, "17324D"),
        "insideH": ("single", 4, "D9D2C4"),
        "left": ("nil", 0, "auto"),
        "right": ("nil", 0, "auto"),
        "insideV": ("nil", 0, "auto"),
    })
    set_tbl_cellmar(t)

    hdr = t.rows[0]
    trPr = hdr._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    trPr.append(th)
    cant = OxmlElement("w:cantSplit")
    trPr.append(cant)

    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.width = Cm(widths[i])
        cell.vertical_alignment = 1
        shade(cell._tc, "EFE9DC")
        # 表头下缘加一条深色细分隔线（三线表中间线）
        tcPr = cell._tc.get_or_add_tcPr()
        tcB = OxmlElement("w:tcBorders")
        for side in ("top", "left", "bottom", "right"):
            el = OxmlElement(f"w:{side}")
            if side == "bottom":
                el.set(qn("w:val"), "single")
                el.set(qn("w:sz"), "8")
                el.set(qn("w:color"), "17324D")
            else:
                el.set(qn("w:val"), "nil")
                el.set(qn("w:sz"), "0")
                el.set(qn("w:color"), "auto")
            tcB.append(el)
        tcPr.append(tcB)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.2
        set_font(p.add_run(h), HEI, 9.5, bold=True, color=INK)

    for row in rows:
        tr = t.add_row()
        trPr = tr._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        for i, val in enumerate(row):
            cell = tr.cells[i]
            cell.width = Cm(widths[i])
            cell.vertical_alignment = 1
            p = cell.paragraphs[0]
            p.alignment = (WD_ALIGN_PARAGRAPH.CENTER if len(str(val)) <= 6
                           else WD_ALIGN_PARAGRAPH.LEFT)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.2
            bold = i == 0 and len(headers) > 2
            set_font(p.add_run(str(val)), SONG, 9.5, bold=bold,
                     color=BLACK if i == 0 else GRAY)
    # 表头与首行不跨页，避免表题孤立在页脚
    for r in t.rows[:2]:
        for cell in r.cells:
            for p in cell.paragraphs:
                p.paragraph_format.keep_with_next = True

    # 表后留白
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(0)
    sp.paragraph_format.line_spacing = 0.6
    set_font(sp.add_run(""), SONG, 6)


def code_block(doc, lines, accent_bar=True):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Cm(0.5)
    pf.space_before = Pt(6)
    pf.space_after = Pt(8)
    pf.line_spacing = 1.15
    para_shade(p, "F7F4ED")
    if accent_bar:
        p_border(p, "left", 18, "C9622F", 6)
    for i, line in enumerate(lines):
        run = p.add_run(line if line else " ")
        set_font(run, MONO, 8.5, color=RGBColor(0x2B, 0x35, 0x3D), latin=MONO)
        if i < len(lines) - 1:
            run.add_break()
    return p


def references(doc, items):
    for i, it in enumerate(items, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Cm(0.9)
        pf.first_line_indent = Cm(-0.9)
        pf.space_after = Pt(4)
        pf.line_spacing = 1.35
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        set_font(p.add_run(f"[{i}]　"), SONG, 10, color=GRAY)
        set_font(p.add_run(it), SONG, 10, color=BLACK)


# ------------------------------------------------------------------ 封面
def cover(doc):
    for _ in range(2):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    set_font(p.add_run("杭州电子科技大学"), HEI, 22, bold=True, color=INK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(30)
    set_font(p.add_run("第二届 AIGC 应用创新大赛"), HEI, 15, bold=False, color=GRAY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    set_font(p.add_run("参 赛 作 品 项 目 文 档"), SONG, 11, color=MUTED)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(26)
    p.paragraph_format.space_after = Pt(2)
    set_font(p.add_run("物　归"), HEI, 46, bold=True, color=INK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    set_font(p.add_run("校园失物智能招领平台"), HEI, 16, color=GRAY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    set_font(p.add_run("GUIWU · A Campus Lost & Found Platform Powered by Multimodal AI"),
             LATIN, 8.5, color=MUTED)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    p_border(p, "bottom", 8, "C9622F", 1)
    p.paragraph_format.space_after = Pt(18)
    set_font(p.add_run("赛题一　AI 辅助开发 · 创意产品原型"), HEI, 12, color=ACCENT)

    info = [("团 队 名 称", "【待填】"),
            ("团 队 成 员", "【待填，共 5 人】"),
            ("所 在 班 级", "【待填】"),
            ("指 导 教 师", "【待填】"),
            ("提 交 日 期", "2026 年 11 月")]
    for k, v in info:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Cm(1.9)
        pf.space_after = Pt(9)
        pf.line_spacing = 1.5
        ts = pf.tab_stops
        ts.add_tab_stop(Cm(5.3), WD_TAB_ALIGNMENT.RIGHT)
        ts.add_tab_stop(Cm(11.9), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.LINES)

        set_font(p.add_run(k + "："), SONG, 11, color=GRAY)
        set_font(p.add_run("\t"), SONG, 11, color=GRAY)
        val = p.add_run(v)
        set_font(val, SONG, 11, color=INK)
        val.font.underline = True
        set_font(p.add_run("\t"), SONG, 11, color=GRAY)

    for _ in range(2):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run("二〇二六年十一月"), SONG, 11, color=GRAY)


def toc(doc):
    doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(18)
    set_font(p.add_run("目　　录"), HEI, 18, bold=True, color=INK)

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    add_field(p, 'TOC \\o "1-3" \\h \\z \\u', "")

    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.paragraph_format.space_before = Pt(18)
    set_font(note.add_run("（目录在打开文档时自动更新；若未显示，请按 Ctrl+A 后按 F9）"),
             SONG, 8, color=MUTED)


def header_footer(sec, first_h1_text=""):
    sec.header.is_linked_to_previous = False
    sec.footer.is_linked_to_previous = False

    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.paragraph_format.space_after = Pt(0)
    set_font(hp.add_run("杭州电子科技大学第二届 AIGC 应用创新大赛　·　「物归」项目文档"),
             SONG, 8, color=MUTED)
    p_border(hp, "bottom", 4, "D9D2C4", 2)

    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(fp.add_run("— "), SONG, 9, color=GRAY)
    for r in add_field(fp, " PAGE ", "1"):
        set_font(r, SONG, 9, color=GRAY)
    set_font(fp.add_run(" —"), SONG, 9, color=GRAY)


def page_number_start(sec, start=1):
    sectPr = sec._sectPr
    pg = sectPr.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType")
        sectPr.append(pg)
    pg.set(qn("w:start"), str(start))


# ------------------------------------------------------------------ 主流程
def build(out):
    doc = Document()
    setup_styles(doc)

    sec = doc.sections[0]
    sec.page_width = Cm(21)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(3.0)
    sec.right_margin = Cm(2.6)
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.header_distance = Cm(1.4)
    sec.footer_distance = Cm(1.4)

    cover(doc)
    toc(doc)

    body_sec = doc.add_section(WD_SECTION.NEW_PAGE)
    body_sec.page_width = Cm(21)
    body_sec.page_height = Cm(29.7)
    body_sec.left_margin = Cm(3.0)
    body_sec.right_margin = Cm(2.6)
    body_sec.top_margin = Cm(2.5)
    body_sec.bottom_margin = Cm(2.5)
    body_sec.header_distance = Cm(1.4)
    body_sec.footer_distance = Cm(1.4)
    header_footer(body_sec)
    page_number_start(body_sec, 1)

    first_h1 = True
    for blk in doc_content.blocks():
        kind = blk[0]
        if kind == "h1":
            p = doc.add_paragraph(blk[1], style="Heading 1")
            if first_h1:
                p.paragraph_format.page_break_before = False
                first_h1 = False
            elif blk[1].startswith(("附录 C", "附录 D", "附录 E")):
                p.paragraph_format.page_break_before = False
        elif kind == "h2":
            doc.add_paragraph(blk[1], style="Heading 2")
        elif kind == "h3":
            doc.add_paragraph(blk[1], style="Heading 3")
        elif kind == "p":
            body(doc, blk[1])
        elif kind == "ul":
            bullets(doc, blk[1])
        elif kind == "table":
            table(doc, blk[1], blk[2], blk[3], blk[4])
        elif kind == "fig":
            figure(doc, blk[1], blk[2], blk[3])
        elif kind == "code":
            code_block(doc, blk[1])
        elif kind == "ref":
            references(doc, blk[1])
        else:
            raise ValueError(kind)

    settings = doc.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    settings.append(uf)

    cp = doc.core_properties
    cp.title = "物归 · 校园失物智能招领平台 — 项目文档"
    cp.author = "杭州电子科技大学第二届 AIGC 应用创新大赛参赛团队"
    cp.subject = "赛题一：AI 辅助开发 · 创意产品原型"

    doc.save(out)
    print("saved", out)


if __name__ == "__main__":
    build(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "物归_项目文档.docx"))
