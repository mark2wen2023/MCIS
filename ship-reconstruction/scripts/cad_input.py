"""离线 CAD 文件登记、转换和表格表头发现。"""
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from core.drawing_parser import fingerprint, parse_drawing
from core.oriented_table import extract_oriented_table
from core.oriented_offsets import offsets_for_review

AXES = "x-forward,y-port,z-up"
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
LABEL = {
    "station": re.compile(rf"(?:ST(?:ATION)?|STA|站位|站)\s*[:=]?\s*({NUMBER})\s*(mm|m)?", re.I),
    "height": re.compile(rf"(?:WL|WATERLINE|水线)\s*[:=]?\s*({NUMBER})\s*(mm|m)?", re.I),
}


def convert(path, out, oda=None):
    if path.suffix.lower() == ".dxf":
        return path, None
    dest = out / (fingerprint(path) + ".dxf")
    with tempfile.TemporaryDirectory() as tmp:
        inp, result = Path(tmp) / "in", Path(tmp) / "out"
        inp.mkdir()
        result.mkdir()
        src = inp / "source.dwg"
        shutil.copyfile(path, src)
        if fingerprint(src) != fingerprint(path):
            raise ValueError("DWG 在读取过程中改变")
        target = result / "source.dxf"
        if oda:
            exe = str(Path(oda).resolve(strict=True))
            command = [exe, str(inp), str(result), "ACAD2013", "DXF", "0", "0", "*.dwg"]
        else:
            exe = shutil.which("dwg2dxf")
            if not exe:
                raise ValueError("需要本机 dwg2dxf 或 --oda 可执行文件")
            command = [exe, "-o", str(target), str(src)]
        process = subprocess.run(command, cwd=tmp, capture_output=True, timeout=150)
        if process.returncode or not target.is_file() or target.is_symlink():
            raise ValueError(f"DWG 转换未生成可读 DXF，退出码 {process.returncode}")
        shutil.copyfile(target, dest)
    return dest, {"tool": Path(exe).name, "tool_sha256": fingerprint(exe),
                  "source_sha256": fingerprint(path), "dxf_sha256": fingerprint(dest)}


def classify(parsed):
    keywords = {"lines": ("型线", "型值", "lines plan", "offset table", "table of offsets"),
                "arrangement": ("总布置", "general arrangement"),
                "structure": ("基本结构", "结构图", "structural plan", "framing plan"),
                "section": ("典型横剖", "中横剖面", "midship section")}
    result = {}
    for kind, terms in keywords.items():
        hits = [e["handle"] for e in parsed["entities"] if any(
            t in str(e.get("text", "")).lower() for t in terms)]
        if hits:
            result[kind] = hits
    return result


def declarations(entities):
    """Only printed declarations establish units, frame or mirror symmetry."""
    import unicodedata
    notes = [(e["handle"], unicodedata.normalize("NFKC", e.get("text", "")).lower())
             for e in entities if e["type"] in ("TEXT", "MTEXT")]
    combined = " ".join(t for _, t in notes)
    def find(pattern):
        return [h for h, t in notes if re.search(pattern, t)]
    unit_pattern = r"(?:half[ -]?breadths?|breadth|offsets?|型值|半宽)(?:\s+(?:values?|units?|in)|数值|单位|采用|均为|以)*\s*[:=：(\[]*\s*(mm|m|毫米|米)\b"
    units = {m.group(1) for _, t in notes for m in re.finditer(unit_pattern, t)}
    units = {{"米":"m","毫米":"mm"}.get(u,u) for u in units}
    frame = (bool(re.search(r"x\s*[-+:=]?\s*(?:forward|向艏|向首)", combined)) and
             bool(re.search(r"y\s*[-+:=]?\s*(?:port|向左舷)", combined)) and
             bool(re.search(r"z\s*[-+:=]?\s*(?:up|向上)", combined)))
    # Avoid treating a negated declaration as permission to mirror.
    sym = find(r"\bsymmetric(?:al)?\b|左右对称|关于中线对称|左右舷对称")
    negative = find(r"\b(?:not|non[- ]?)\s*symmetric|不对称|非对称")
    return {"unit":next(iter(units)) if len(units)==1 else None, "frame":frame,
            "symmetric":bool(sym and not negative), "notes":[h for h,t in notes if
                re.search(unit_pattern,t) or any(w in t for w in ("forward","向艏","向首","对称","symmetr"))]}


def discover(parsed):
    entities = [e for e in parsed["entities"] if e["layout"] == "Model"]
    declared = declarations(entities)
    axes = {}
    for family, pattern in LABEL.items():
        values = {}
        for e in entities:
            label = e.get("text")
            if not isinstance(label, str):
                continue
            m = pattern.fullmatch(label.strip())
            if m and m.group(2):
                value = float(m.group(1)) * (0.001 if m.group(2).lower()=="mm" else 1.)
                values[label.strip()] = value
        if len(values) < 2 or len(set(values.values())) != len(values):
            return None
        axes[family] = dict(sorted(values.items(),key=lambda pair:pair[1]))
    if not declared["unit"] or not declared["frame"]:
        return None
    return {"axes":axes,"declarations":declared}


def extract(parsed, config=None):
    if config:
        configs = [config]
        declared = None
    else:
        found = discover(parsed)
        if not found:
            return None
        declared = found["declarations"]
        axes = found["axes"]
        configs=[]
        for role in ("row","column"):
            r,c = (axes["station"],axes["height"]) if role=="row" else (axes["height"],axes["station"])
            for rev_r in (False,True):
                for rev_c in (False,True):
                    configs.append(dict(row_labels=list(reversed(r)) if rev_r else list(r),
                        column_labels=list(reversed(c)) if rev_c else list(c),station_axis=role,
                        stations_m_by_label=axes["station"],heights_m_by_label=axes["height"],
                        unit=declared["unit"],source="DXF:"+",".join(declared["notes"]),tolerance=1e-5))
    answers={}
    for opt in configs:
        table = extract_oriented_table(parsed, row_labels=opt["row_labels"],column_labels=opt["column_labels"],
            layout=opt.get("layout","Model"),plane_z=opt.get("plane_z",0),tolerance=opt["tolerance"])
        if table["issues"] or not table["cells"]:
            if config:
                raise ValueError("型值表未唯一定位或存在冲突："+str(table["issues"][:3]))
            continue
        mapped = offsets_for_review(table,station_axis=opt["station_axis"],
            stations_m_by_label=opt["stations_m_by_label"],heights_m_by_label=opt["heights_m_by_label"],
            unit=opt["unit"],mapping_source={"document_id":parsed["document"]["sha256"],"locator":opt["source"]})
        rows=[]
        for v in mapped["rows"]:
            cell=v["source"]["table_cell"]
            rows.append(dict(x_m=v["station_x_m"],z_m=v["height_z_m"],breadth_m=v["half_breadth_m"],
                raw=cell["texts"][0]["raw_text"] if cell["texts"] else None,
                handle=cell["texts"][0]["handle"] if cell["texts"] else None,
                row_header=cell["row_header"]["handle"],column_header=cell["column_header"]["handle"],
                provenance="drawing" if cell["texts"] else "unknown"))
        key=tuple((row["x_m"],row["z_m"],row["handle"]) for row in rows)
        answers[key]=(rows,table,declared,opt)
    if len(answers)>1:
        raise ValueError("存在多个可行的表格坐标映射")
    return next(iter(answers.values()),None)
