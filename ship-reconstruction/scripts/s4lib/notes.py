"""识别结构注记的字面证据。图面尺寸、图形单位和船轴定位分别处理。"""
import re
import unicodedata

ALIASES = (
    ("strong_beam", r"强横梁|strong\s*(?:deck\s*)?beam|web\s*beam"),
    ("transverse_bulkhead", r"横(?:向|水密)?(?:舱|隔)壁|transverse\s*bulkhead"),
    ("longitudinal_bulkhead",r"纵(?:向|水密)?(?:舱|隔)壁|longitudinal\s*bulkhead"),
    ("floor",r"实肋板|肋板|solid\s*floor"),
    ("frame",r"肋骨|(?:web|transverse|ordinary)\s*frame|\bframe\b(?!\s*spacing)"),
    ("longitudinal",r"纵骨|纵桁|纵向加强筋|longitudinal(?:\s*stiffener)?"),
    ("stiffener",r"加强筋|扶强材|加强材|stiffener"),
    ("beam",r"横梁|\bbeam\b"),
    ("double_bottom_plate",r"双层底|内底板|内底顶板|double\s*bottom|inner\s*bottom|tank\s*top"),
    ("bulkhead",r"舱壁|隔壁|bulkhead"),
    ("deck",r"甲板|\bdeck\b"),
    ("tank",r"压载舱|(?:水|油)柜|液舱|\btank\b"),
    ("compartment",r"货舱|机舱|舱室|compartment|cargo\s*hold"),
    ("bracket",r"肘板|连接板|bracket|gusset"),
    ("plate",r"外板|舷板|底板|平板|钢板|板料|\bplate\b"),
)
NUM=r"(?:\d+(?:\.\d+)?|\.\d+)"
UNIT=r"(?:mm|cm|m|毫米|厘米|米)"
SEP=r"\s*[x×*]\s*"
UNIT_VALUE={"mm":"mm","毫米":"mm","cm":"cm","厘米":"cm","m":"m","米":"m"}
FR=r"(?:fr(?:ame)?\.?\s*#?|肋位\s*|肋号\s*|肋骨号\s*)"
RANGE=re.compile(FR+r"("+NUM+r")\s*(?:[-~～—–至到]\s*(?:"+FR+r")?("+NUM+r"))?",re.I)
PROFILE=re.compile(r"(?<![a-z])(?P<family>HP|FB|FLAT\s*BAR|BULB\s*FLAT|ANGLE|PL|L|T|I|H|Ø|Φ|∠|扁钢|球扁钢|角钢)\s*[-:]?\s*(?P<values>"+NUM+r"(?:(?:"+SEP+r"|\s*/\s*)"+NUM+r"){1,4})(?:\s*(?P<unit>"+UNIT+r"))?(?![\d.])",re.I)
QUANTITIES=(
    ("thickness",r"(?<![a-z])(?:t|thk|thickness)\b\s*[:=]?|板厚\s*[:=]?|厚度?\s*[:=]?"),
    ("spacing",r"肋距\s*(?:s\s*=)?|间距\s*[:=]?|spacing\s*[:=]?|@\s*"),
    ("length",r"长度?\s*[:=]|length\s*[:=]"),
    ("width",r"宽度?\s*[:=]|width\s*[:=]"),
    ("height",r"高度?\s*[:=]|height\s*[:=]"),
)
SIZES=[(k,re.compile("(?:"+rg+")\\s*("+NUM+")\\s*("+UNIT+")?",re.I)) for k,rg in QUANTITIES]
IDENT=re.compile(r"(?:构件编号|构件号|编号|\bID)\s*[:=#：]\s*([\w.-]+)",re.I)
STOCK=re.compile(r"(?<![a-zA-Z0-9.])[-−]\s*("+NUM+")"+SEP+"("+NUM+")(?:"+SEP+"("+NUM+"))?(?:\\s*("+UNIT+"))?",re.I)


def normalized(text):
    return unicodedata.normalize("NFKC", text).replace("%%C","Ø").replace("%%c","Ø").replace("%%U","").replace("%%u","")


def parse(text):
    s=normalized(text).strip()
    compact=re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])","",s)
    roles=[key for key,rg in ALIASES if re.search(rg,compact,re.I)]
    dims=[]
    for kind,pattern in SIZES:
        for m in pattern.finditer(s):
            dims.append(dict(kind=kind,value=float(m[1]),unit=UNIT_VALUE.get((m[2] or "").lower()),raw=m[0].strip()))
    profiles=[]
    for m in PROFILE.finditer(s):
        profiles.append(dict(family=m["family"].upper(),values=[float(v) for v in re.findall(NUM,m["values"])],unit=UNIT_VALUE.get((m["unit"] or "").lower()),raw=m[0].strip()))
    for m in STOCK.finditer(s):
        profiles.append(dict(family="PL",values=[float(v) for v in m.groups()[:3] if v],unit=UNIT_VALUE.get((m[4] or "").lower()),raw=m[0].strip()))
    ranges=[dict(start=float(m[1]),end=float(m[2] or m[1]),raw=m[0]) for m in RANGE.finditer(s)]
    id_match=IDENT.search(s)
    repeat=re.search(r"每(?:隔)?\s*(\d+)\s*(?:档|肋位|肋距)|隔肋设|每肋(?:位)?设|every\s+(\d+)\s+frames?",s,re.I)
    material=re.search(r"(?:材料|材质|material|steel grade)\s*[:=：]\s*([A-Z][A-Z0-9-]*)\b",s,re.I)
    if not any([roles,dims,profiles,ranges,id_match,repeat]):
        return None
    levels=[m[0] for m in re.finditer(r"主甲板|驾驶甲板|上甲板|下甲板|顶[篷蓬]甲板|走道甲板|内底板|main deck|upper deck|lower deck",compact,re.I)]
    role=roles[0] if roles else "unknown"
    directional={"longitudinal":"longitudinal","longitudinal_bulkhead":"longitudinal","transverse_bulkhead":"transverse","strong_beam":"transverse","frame":"transverse","floor":"transverse"}
    return dict(type=role,mentioned_types=roles,dimensions=dims,profiles=profiles,frame_ranges=ranges,
                identity=id_match[1] if id_match else None,axis_direction=directional.get(role),
                direction_basis="role_term" if role in directional else None,material=material[1] if material else None,
                repetition=repeat[0] if repeat else None,deck_levels=levels)
