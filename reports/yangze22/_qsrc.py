# -*- coding: utf-8 -*-
"""Quote locator for YANGZE 22 report.txt: whitespace-insensitive search, page/line mapping.

report.txt 是 pdftotext 导出的文本；正文页脚为单独一行的页码（1..51）。
页码规则：某行之后遇到的第一个页脚数字就是它所在的正文页；PDF 页 = 正文页 + 2。
第 1–53 行是封面与目录（PDF 第 1–2 页）。
归一化：删除页脚行，再删除全部空白字符。引文必须在归一化文本中逐字出现。
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
TXT = HERE / "report.txt"
FRONT_LAST_LINE = 53


class Locator:
    def __init__(self, path=TXT):
        self.lines = path.read_text(encoding="utf-8").split("\n")
        # detect footers: digit-only lines forming the increasing sequence 1,2,3...
        expected = 1
        self.footer = {}  # line_no(1-based) -> page
        for i, l in enumerate(self.lines, start=1):
            s = l.strip()
            if i > FRONT_LAST_LINE and re.fullmatch(r"\d{1,2}", s) and int(s) == expected:
                self.footer[i] = expected
                expected += 1
        self.max_page = expected - 1
        # page per line
        self.page_of = {}
        pending = []
        for i in range(1, len(self.lines) + 1):
            if i <= FRONT_LAST_LINE:
                self.page_of[i] = None
                continue
            pending.append(i)
            if i in self.footer:
                for j in pending:
                    self.page_of[j] = self.footer[i]
                pending = []
        for j in pending:
            self.page_of[j] = self.max_page
        # normalized text + char->line map
        buf, owner = [], []
        for i, l in enumerate(self.lines, start=1):
            if i in self.footer:
                continue
            for ch in l:
                if not ch.isspace():
                    buf.append(ch)
                    owner.append(i)
        self.norm = "".join(buf)
        self.owner = owner

    @staticmethod
    def n(q):
        return re.sub(r"\s+", "", q or "")

    def find(self, quote):
        qn = self.n(quote)
        if not qn:
            return None
        k = self.norm.find(qn)
        if k < 0:
            return None
        l1 = self.owner[k]
        l2 = self.owner[k + len(qn) - 1]
        count = self.norm.count(qn)
        return {"lineStart": l1, "lineEnd": l2, "page": self.page_of[l1], "occurrences": count}


LOC = Locator()
MISSING = []


def src(quote, figure=None, note=None, reading=None):
    """Build a source dict. quote must exist in report.txt (whitespace-insensitive)."""
    hit = LOC.find(quote)
    if hit is None:
        MISSING.append(quote)
        d = {"page": None, "pdfPage": None, "line": None, "quote": quote}
    else:
        page = hit["page"]
        pdf = (page + 2) if page is not None else (1 if hit["lineStart"] <= 9 else 2)
        d = {
            "page": page if page is not None else "封面/目录",
            "pdfPage": pdf,
            "line": hit["lineStart"] if hit["lineStart"] == hit["lineEnd"] else f"{hit['lineStart']}-{hit['lineEnd']}",
            "quote": quote,
        }
    if figure:
        d["figure"] = figure
    if reading:
        d["figureReading"] = reading
    if note:
        d["note"] = note
    return d
