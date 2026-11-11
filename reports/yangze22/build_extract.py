# -*- coding: utf-8 -*-
"""Build YANGZE 22 / VEGA DREAM case.json, ecfc.json(.svg/.png), _quote_checks.json, tracks_from_report.csv.

运行：/workspace/.venv-reports/bin/python build_extract.py
数据全部来自公开调查报告 report.pdf / report.txt；本机抽取，未调用任何外部模型。
"""
from __future__ import annotations
import csv, json, sys, importlib.util
sys.dont_write_bytecode = True
from pathlib import Path

OUT = Path(__file__).parent
sys.path.insert(0, str(OUT))
import _qsrc
from _qsrc import src, LOC
from build_case import (bt, Y, V, LOC_REPORT, vessels, personnel, environment, damage_and_collision,
                        consequences, causes_liability)
from build_timeline import timeline, rudder_table, track_points

# reuse Haili5 ECFC validator (表4 规则)
_spec = importlib.util.spec_from_file_location("hb", OUT.parent / "haili5" / "build_extract.py")
hb = importlib.util.module_from_spec(_spec)
sys.modules["hb"] = hb
_spec.loader.exec_module(hb)
hb.CN_VERBS = hb.CN_VERBS + ("操", "离开", "接班", "越过", "侵入", "破损", "泄漏", "报告", "压舵", "误压")
node, edge = hb.node, hb.edge


def discrepancies():
    return [
        {"id": "X01", "topic": "YANGZE 22 开航时间", "values": ["约0900时（航次及载货情况）", "约0830时（事故经过）"],
         "sources": [src("2024年12月30日约0900时，“YANGZE 22”轮从南通新世界通用码头开航"), src("2024年12月30日约0830时，该轮从南通新世界通用码头开航。")]},
        {"id": "X02", "topic": "碰撞时间写法", "values": ["约2202时（简况、气象水文）", "2201时54秒（认定）"],
         "sources": [src("事故发生时间约为2202时，正值涨水。"), src("认定本起碰撞事故发生的时间为2024年12月")], "resolution": "以认定时刻 22:01:54 为准，约2202时为取整"},
        {"id": "X03", "topic": "VDR 屏显时刻与正文时刻", "values": ["正文 2200:14 / 2200:45 / 2201:09 / 2201:21 / 2202:52 / 2206:21 / 2159:07 / 2159:45",
                                                         "VDR UTC 14:00:12–13 / 14:00:44 / 14:01:08 / 14:01:20 / 14:02:51 / 14:06:20 / 13:59:06 / 13:59:44"],
         "note": "VDR 截图时刻普遍比正文早 1 秒（2158:30 与 2201:54 两处一致）。VDR 的 LMT 字段与 UTC 相同，即 VDR 未设本地时；正文已换算成北京时间。",
         "sources": [src("图14：2200时14秒“YANGZE 22”轮VDR记录情况", figure="图14", reading="UTC/LMT 14:00:12"),
                     src("图24：2200时45秒“YANGZE 22”轮VDR记录和吴淞VTS监控", figure="图24", reading="UTC/LMT 14:00:44")]},
        {"id": "X04", "topic": "ROT 正文与 VDR 屏显", "values": ["2200:14 正文 P16.8°/min；图14 P15.8、图22 P16.3", "2144:44 正文 P1.6°/min；图18 P2.7"],
         "sources": [src("2200时14秒，该轮航向约109°，航速约9.3节，ROT:P16.8°/min"), src("图18：2144时44秒“YANGZE 22”轮VDR记录和吴淞VTS监控", figure="图18", reading="ROT P2.7，Heading 120.2")]},
        {"id": "X05", "topic": "VEGA DREAM 21:58:30 位置", "values": ["2158:30 位于41号灯浮上游进口航道内", "2159:45 位于38号灯浮下游进口航道内"],
         "note": "进口船上行，75 秒内不可能从41号灯浮上游退到38号灯浮下游；YANGZE 22 出口方向依次经过41→39号灯浮，说明灯浮编号向下游递减。疑为“41号灯浮下游”笔误或灯浮号错写，未改动",
         "sources": [src("“VEGA DREAM”轮位于41号灯浮上游进口航道内正常航行"), src("2159时45秒，该轮位于38号灯浮下游进口航道内正常航行")]},
        {"id": "X06", "topic": "舵角：表3/正文与 VDR 屏显", "values": ["2200:14 表3 指令左舵29°、反馈左舵30°；正文“实际操左舵29°”", "图14（14:00:12）舵角 P23.8，图22（14:00:13）P23.5"],
         "note": "屏显值可能是该秒的瞬时舵角，表3可能取该舵令后的稳定值；两者并存",
         "sources": [src("2200时14秒109°右满舵左舵29°左舵30°"), src("图22：2200时14秒“YANGZE 22”轮VDR记录和吴淞VTS监控", figure="图22", reading="舵角 P23.5")]},
        {"id": "X07", "topic": "VEGA DREAM 是否收到 CH06 呼叫", "values": ["引航员杜**未听到其呼叫", "VEGA DREAM 轮虽然在VHF CH06频道收到上述呼叫"],
         "note": "前者说引航员本人未听到，后者说船舶在频道上收到（VDR 可能录到），并非直接矛盾；笔录比对时应区分“设备收到”与“人员听到”",
         "sources": [src("但引航员杜**未听到其呼叫，两船未建立起联系。"), src("“VEGA DREAM”轮虽然在VHF CH06频道收到上述呼叫，但两船未建立有效通信联系。")]},
        {"id": "X08", "topic": "VEGA DREAM 抛锚时刻", "values": ["31日约0345时在宝山北锚地抛锚（事故经过）", "约0350时抵达宝北锚地抛锚（应急处置）"],
         "sources": [src("31日约0345时，该轮在宝山北锚地抛锚"), src("约0350时，“VEGA DREAM”轮在拖轮“东雷50”轮、“兴晟201”轮伴航下抵达宝北锚地抛锚")]},
        {"id": "X09", "topic": "碰撞时航速/航向", "values": ["YANGZE 22 正文航向约047°、航速约8.0节", "图6 AIS 航向54°、航速7.9kn、船首向47.0；图27 VDR Heading 48.0"],
         "note": "正文“航向”数值与 VDR/AIS 船首向吻合，应理解为船首向而非对地航向",
         "sources": [src("2201时54秒，该轮航向约047°，航速约8.0节。"), src("图6：碰撞时间和位置图", figure="图6", reading="YANGZE 22 航向54° 航速7.9kn 船首向47.0")]},
        {"id": "X10", "topic": "两船距离与 AIS 船位间距", "values": ["2200:42 正文两船相距约0.3海里", "图29 两船 AIS 船位间距约0.53海里（推算）"],
         "note": "报告距离可能是船体（雷达回波）间距，AIS 船位是天线位置；两船船长 225/283 m，天线偏移报告未给，二者不能直接比较",
         "sources": [src("两船相距约0.3海里，CPA约0.1海里，TCPA约1分钟。"), src("图29：2200时42秒吴淞VTS监控", figure="图29")]},
        {"id": "X11", "topic": "SD 卡数据时段的时间基准", "values": ["正文：21:50:00至22:10:00", "图12/图13 标题：UTC 13:50~14:10"],
         "note": "正文按北京时间叙述，YDK 图表按 UTC；同一段数据，相差 8 小时",
         "sources": [src("2024年12月30日21:50:00至22:10:00的数据"), src("图13：“YANGZE 22”轮事发时段船首向和转率SD数据卡记录情况", figure="图13", reading="标题 2024/12/30 UTC 13:50~14:10 Heading/ROT")]},
        {"id": "X12", "topic": "AIS 静态数据与证书", "values": ["YANGZE 22 证书船长225.29 m / AIS 229.0 m；ETA 08-01-2024", "VEGA DREAM 证书船长283.3 m / AIS 290.0 m"],
         "sources": [src("船长：225.29米"), src("船长：283.3米"), src("图6：碰撞时间和位置图", figure="图6")]},
        {"id": "X13", "topic": "油污清除完毕时间", "values": ["至2025年1月2日各相关水域水面油污已清除完毕", "1月2日约1720时仅横沙通道新民港附近有少量油污；3日约1700时现场油污全部清除"],
         "note": "口径不同（水面 vs 现场含岸滩），并存",
         "sources": [src("至2025年1月2日，各相关水域水面油污已清除完毕"), src("3日约1700时，现场油污已全部清除完毕。")]},
    ]


def missing_data():
    return [
        "两船完整 AIS / VDR / 雷达原始数据未附；只有正文时刻点和 VDR/VTS 截图，VDR 截图里 SOG 栏为空、COG 不可读。",
        "VEGA DREAM 的 VDR 截图一张也没有；其车钟、舵令的逐条时刻（2200:42 之后连续下令前进一、微速进、停车、正舵、后退三）和实际执行情况未给。",
        "VEGA DREAM 在 2200:42 之前只有航向航速，船位仅 2200:38（正文 0.1′ 精度，图28 0.001′）、2200:42（图29）、2201:54（图6）三个点。",
        "灯浮（41、39、38号等）、航道分隔线、航道边线坐标与航道走向未给；碰撞概位只到 0.1′。",
        "风向、流向没有度数，风速没有 m/s，浪高未给；潮高基准面未写。",
        "船员工作/休息时间记录未给（仅丁**白班作息安排），无法做 STCW A-VIII/1 / MLC 工休合规计算；疲劳只能定性推断。",
        "船舶排水量、操纵性参数（旋回、Nomoto K/T、舵速）、天线位置未给；仿真需从同型船或默认值估算。",
        "VEGA DREAM 收到 CH06 呼叫的 VDR 录音内容、YANGZE 22 驾驶台对话原文未附；“舵效很差”等陈述只有转述。",
        "YDK SD 卡数据只有图12、图13 两张曲线图，没有数值表。",
        "直接经济损失金额未给。",
        "VEGA DREAM 未采取应急抛锚的认定没有列出所违反的具体条款。",
        "图3（通航情况）、图7（碰撞角度）、图4/5（破口位置）只能定性使用，无比例尺。",
    ]


def ecfc_data():
    S = src
    N = [
        node("E01", "Event", "水手意图用右舵却操左舵压舵", 0, time=bt(21, 59, 7), vessel=Y,
             quantities={"航向": "114°", "舵角": "左5°~10°", "持续": "约30秒"}, cause_role="direct",
             source=S("水手丁**意图使用右舵把定航向，但在此之后约30秒时间内，其实际操左舵5°~10°压舵，导致船首开始向左偏转。"), layout=(0, 0)),
        node("E02", "Event", "水手操左舵至左满舵致船首加速左偏", 0, time=bt(21, 59, 45), vessel=Y,
             quantities={"ROT": "P2.8°/min", "相距": "约0.7海里"}, cause_role="direct",
             source=S("水手丁**随后操左舵15°至左满舵的大舵角压舵，船首随之加快向左偏转。"), layout=(1, 0)),
        node("E03", "Event", "引航员下令右满舵水手反向操左舵", 0, time=bt(22, 0, 14), vessel=Y,
             quantities={"舵令": "右满舵", "实际": "左舵29°", "CPA": "约0.1海里", "TCPA": "约1.6分钟"}, cause_role="direct",
             source=S("引航员周**下令“右满舵”，水手丁**回复“右满舵”，但实际操左舵29°，实际操舵与引航员舵令相反。"), layout=(2, 0)),
        node("E04", "Event", "船首越过分隔线侵入进口航道形成紧迫危险", 0, time=bt(22, 0, 45), vessel=Y,
             quantities={"航向": "092°", "ROT": "P40.4°/min", "相距": "约0.3海里"}, cause_role="direct",
             source=S("船首已越过航道分隔线侵入进口航道。"), layout=(3, 0)),
        node("E05", "Event", "引航员下令左满舵水手反向操右舵", 0, time=bt(22, 1, 21), vessel=Y,
             quantities={"舵令": "左满舵", "实际": "右舵35°", "相距": "约0.1海里"}, cause_role="direct",
             source=S("下令“左满舵”意图减小碰撞角度，水手丁**回复“左满舵”，但实际操右舵35°，与引航员舵令相反。"), layout=(4, 0)),
        node("E06", "Event", "VEGA DREAM船首与YANGZE 22右舷5舱碰撞", 0, time=bt(22, 1, 54), incident=True,
             quantities={"地点": "31°16.9′N 121°49.7′E", "碰撞角": "约70°", "YANGZE 22": "047°/8.0节", "VEGA DREAM": "297°/10.2节"},
             cause_role="direct", source=S("认定本起碰撞事故发生的时间为2024年12月"), layout=(5, 0)),
        node("E07", "Event", "YANGZE 22第5货舱和1号右燃油舱破损进水", 0, time=bt(22, 1, 54, approx=True), vessel=Y,
             quantities={"破口": "约12×16米", "货损": "硫酸铵约8750吨"}, cause_role="consequence",
             source=S("第5号货舱和1号右燃油舱破损。"), layout=(6, 0)),
        node("E08", "Event", "约171吨燃油泄漏造成水面和岸滩污染", 0, time=bt(22, 3, approx=True), vessel=Y,
             quantities={"溢油": "约171.053吨", "岸滩": "约1.5海里、约9000平方米"}, cause_role="consequence",
             source=S("1号右油舱内共计约171.053吨燃油泄漏入江。"), layout=(7, 0)),
        # lane +1 YANGZE 22 bridge
        node("E11", "Event", "水手误压右舵致船首异常右偏", 1, time=bt(21, 44, 15), vessel=Y,
             quantities={"航向": "117°", "ROT": "S13.2°/min"}, cause_role="context",
             source=S("水手丁**查看舵轮后意识到压了右舵，立即使用正舵、左满舵把定航向。"), layout=(-2, 1)),
        node("E12", "Event", "船长离开驾驶台未告知引航员", 1, time=bt(21, 51, approx=True), vessel=Y, cause_role="indirect",
             source=S("随后船长邹**离开驾驶台，未告知引航员周**。"), layout=(-1, 1)),
        node("E13", "Event", "水手报告引航员舵效很差", 1, time=bt(22, 0, 4), vessel=Y, quantities={"实际舵角": "左28°"},
             cause_role="direct", source=S("水手丁**告知引航员周**“现在舵效很差”。"), layout=(1.4, 1)),
        node("C11", "Condition", "三副未对舵令执行进行有效检查", 1, vessel=Y, cause_role="direct",
             source=S("值班三副未对操舵水手舵令执行情况进行有效检查，并及时纠正。"), layout=(2.6, 1)),
        node("C12", "Condition", "驾驶台人员误判为舵效差", 1, vessel=Y, cause_role="direct",
             source=S("驾驶台人员未能结合当时的情况进行充分评估，错误判断为舵效差。"), layout=(3.7, 1)),
        node("C13", "Condition", "未用非随动或越控操舵也未停车倒车", 1, vessel=Y, cause_role="direct",
             source=S("但未采取非随动操舵或越控操舵操纵本船，也未采取停车、倒车等应急措施。"), layout=(4.8, 1)),
        # lane +2 latent
        node("E15", "Event", "船长发现原操舵水手操反舵并更换", 2, time=bt(9, 14, approx=True), vessel=Y, cause_role="indirect",
             source=S("船长邹**发现操舵水手李**出现操反舵的情况，遂通知大副更换操舵水手。"), layout=(-2, 2)),
        node("E16", "Event", "白班水手丁接班操舵", 2, time=bt(19, 36, approx=True), vessel=Y, cause_role="context",
             source=S("约1936时，水手丁**到驾驶台接班操舵。"), layout=(-1, 2)),
        node("C14", "Condition", "丁为白班水手未在本船驾驶台值过班", 2, vessel=Y, cause_role="context",
             source=S("未在驾驶台值过班。"), layout=(0.2, 2)),
        node("C15", "Condition", "未对接替操舵水手进行针对性培训", 2, vessel=Y, cause_role="indirect",
             source=S("但未对接替的操舵水手进行针对操舵培训。"), layout=(1.4, 2)),
        node("C16", "Condition", "手轮刻度盘与操舵方向相反", 2, vessel=Y, presumptive=True, cause_role="context",
             source=S("指针指示的刻度与操舵方向相反。", note="报告在操舵系统描述与安全建议中提及，未明确认定为原因，故标推定"),
             layout=(2.6, 2)),
        node("C17", "Condition", "公司未培训越控操舵模式", 2, vessel=Y, cause_role="indirect",
             source=S("管理公司未对该轮操舵系统进行针对性培训和指导，尤其是越控操舵模式的指导"), layout=(4.8, 2)),
        # lane -1 VEGA DREAM & comms
        node("E21", "Event", "引航员在CH06呼叫对方引航员姓名", -1, time=bt(22, 0, 24), vessel=Y, cause_role="indirect",
             source=S("引航员周**使用VHF CH06频道呼叫“VEGA DREAM”轮引航员名字“杜**，杜**，往右转，我右满舵没舵效”。"), layout=(2.4, -1)),
        node("C21", "Condition", "两船未建立有效联系", -1, cause_role="indirect",
             source=S("但两船未建立有效通信联系。"), layout=(3.5, -1)),
        node("E22", "Event", "VEGA DREAM引航员下令右满舵并连续改车至后退三", -1, time=bt(22, 0, 42), vessel=V,
             quantities={"相距": "约0.3海里", "TCPA": "约1分钟"}, cause_role="context",
             source=S("便立即下令前进二（已在前进二位置）和右满舵，发出一长声警示声号"), layout=(4.6, -1)),
        node("C23", "Condition", "VEGA DREAM未采取应急抛锚", -1, vessel=V, cause_role="direct",
             source=S("“VEGA DREAM”轮未采取应急抛锚等有效措施。"), layout=(5.7, -1)),
        # lane -2 environment / comms practice
        node("C22", "Condition", "引航员间直呼姓名不呼船名呼号", -2, cause_role="indirect",
             source=S("未呼叫对方船名和呼号，导致无法被对方船舶的其他驾驶值班人员接收的情形"), layout=(2.4, -2)),
        node("C31", "Condition", "管制时段进出深水航道船舶密度大", -2, cause_role="context",
             source=S("本起事故发生时正处于长江口深水航道交通管制时段，进出深水航道船舶密度较大。"), layout=(3.6, -2)),
        node("C32", "Condition", "航道宽约350米会遇时间不到2分钟", -2, cause_role="indirect",
             source=S("两船相对速度约19.8节、会遇时间不到2分钟"), layout=(5.0, -2)),
    ]
    E = [
        edge("s01", "E01", "E02", "Sequence", True), edge("s02", "E02", "E03", "Sequence", True),
        edge("s03", "E03", "E04", "Sequence", True), edge("s04", "E04", "E05", "Sequence", True),
        edge("s05", "E05", "E06", "Sequence", True), edge("s06", "E06", "E07", "Sequence", True),
        edge("s07", "E07", "E08", "Sequence", True),
        edge("s11", "E15", "E16", "Sequence"), edge("s12", "E16", "E11", "Sequence"), edge("s13", "E11", "E01", "Sequence"),
        edge("s14", "E12", "E01", "Sequence"), edge("s15", "E13", "E03", "Sequence"),
        edge("s16", "E21", "E22", "Sequence"), edge("s17", "E22", "E06", "Sequence"),
        edge("i01", "C14", "E01", "Influence"), edge("i02", "C15", "E01", "Influence"), edge("i03", "C16", "E01", "Influence"),
        edge("i04", "C11", "E03", "Influence"), edge("i05", "C11", "E05", "Influence"),
        edge("i06", "C12", "C13", "Influence"), edge("i07", "C13", "E04", "Influence"), edge("i08", "C17", "C13", "Influence"),
        edge("i09", "C22", "C21", "Influence"), edge("i10", "C21", "E04", "Influence"),
        edge("i11", "C23", "E06", "Influence"), edge("i12", "C31", "E04", "Influence"), edge("i13", "C32", "E06", "Influence"),
        edge("i14", "C12", "E03", "Influence"),
    ]
    for n in N:
        s = n.get("source") or {}
        if s.get("page") and not n["evidenceIds"]:
            n["evidenceIds"] = [f"report:p{s['page']}", f"report:line{s.get('line')}"]
    return {
        "schemaVersion": "1.0.0", "caseId": "CJK-2024-1230-YangZe22-VegaDream",
        "standard": "论文2.5节 / 表4（Buys 1995, Sklet 2002）；架构4.9节 EcfcValidator（复用 haili5/build_extract.py 的 validate_ecfc）",
        "isDraft": True, "isFictionalDemo": False, "isPublicReport": True,
        "nodes": N, "edges": E,
        "liabilityMapping": {
            "directCauseNodeIds": {"DC1": ["E01", "E02", "E03", "E05"], "DC2": ["C11"], "DC3": ["C12", "C13"], "DC4": ["C23"]},
            "indirectCauseNodeIds": {"IC1": ["E12"], "IC2": ["E21", "C21"], "IC3": ["C32"]},
            "findingNodeIds": {"F1": ["C17"], "F2": ["E15", "C15"], "F3": ["C22"]},
            "yangze22": "主要责任（操舵水手错误执行引航员指令、三副未有效监舵、紧急情况下措施不当）",
            "vegaDream": "次要责任（未采取应急抛锚等有效措施）",
        },
        "notes": [
            "主序列从 21:59:07 误操左舵起笔，到碰撞和溢油污染；21:44 那次误压右舵是同一水手的前兆事件，报告未把它列为原因，标 context。",
            "操舵系统经测试工况正常，属于排除项，没有画成条件节点，记录在 case.json steeringGear.conclusion。",
            "C16（手轮刻度盘与操舵方向相反）报告只在设备描述和安全建议里出现，未直接认定为原因，按推定节点（虚线）处理。",
        ],
    }


def draw_ecfc(doc, issues, outfile, svgfile):
    """沿用 haili5 的绘图样式，改标题、泳道和日期。"""
    import types
    code = Path(hb.__file__).read_text(encoding="utf-8")
    start = code.index("def draw_ecfc(")
    end = code.index("def main():")
    fn_src = code[start:end]
    fn_src = fn_src.replace("广州“10·25”海力5 轮与 WAN HAI A17 轮碰撞事故  ECFC 草稿",
                            "长江口“12·30”YANGZE 22 轮与 VEGA DREAM 轮碰撞事故  ECFC 草稿")
    fn_src = fn_src.replace('startswith("2025-10-25")', 'startswith("2024-12-30")')
    fn_src = fn_src.replace('"次序列　应急电源"', '"（空）"').replace('"次序列　机电隐患"', '"次序列　人员与培训（潜在条件）"')
    fn_src = fn_src.replace('"次序列　海力5驾驶台/机舱"', '"次序列　YANGZE 22 驾驶台"')
    fn_src = fn_src.replace('"次序列　WAN HAI A17 驾驶台"', '"次序列　通信与 VEGA DREAM"')
    fn_src = fn_src.replace('"次序列　瞭望与操舵"', '"通航环境与通信方式"')
    fn_src = fn_src.replace("非虚构案件（IsFictionalDemo=false）。", "公开报告真实案件（IsFictionalDemo=false）。")
    fn_src = fn_src.replace('ax.text(xmin + 0.15, 3 * 2.15, "（空）", ha="left", va="center", fontproperties=fp, fontsize=7, color="#555")', "")
    fn_src = fn_src.replace("xmin, xmax = min(xs) - 2.2", "xmin, xmax = min(xs) - 4.4")
    ns = {}
    exec(compile("from pathlib import Path\n" + fn_src, "draw_ecfc", "exec"), ns)
    ns["draw_ecfc"](doc, issues, outfile, svgfile)


def verify_all(case, ecfc):
    """核对 case.json 与 ecfc.json 中每一条 source.quote。"""
    rows = []
    def walk(o, path):
        if isinstance(o, dict):
            if "quote" in o and isinstance(o.get("quote"), str) and ("page" in o or "line" in o):
                hit = LOC.find(o["quote"])
                rows.append({"path": path, "page": o.get("page"), "line": o.get("line"), "figure": o.get("figure"),
                             "quote": o["quote"], "matched": hit is not None,
                             "occurrences": hit["occurrences"] if hit else 0})
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                ident = v.get("id") or v.get("nodeId") if isinstance(v, dict) else None
                walk(v, f"{path}[{ident or i}]")
    walk(case, "case")
    walk(ecfc, "ecfc")
    return rows


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_tracks_csv(points, path, case_label):
    cols = ["vesselId", "timeBeijing", "timeUtc", "approximate", "latDeg", "lonDeg", "cogDeg", "sogKn", "hdgDeg",
            "rotDegPerMin", "stwKn", "rudderDeg", "propellerRpm", "positionText", "provenance", "page", "pdfPage", "line",
            "figure", "figureReading", "quote", "note"]
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(f"# {case_label}：航迹样本，取自调查报告正文文字和报告插图（VDR/VTS 截图）读数，不是 AIS 原始数据。\n")
        f.write("# provenance: ReportNarrative=正文文字；ReportFigure-VDR=VDR 回放截图图读；ReportFigure-AIS=VTS 截图中的 AIS 信息框图读。\n")
        f.write("# 正文“航向”与 VDR/AIS 船首向数值吻合，cogDeg 列对 ReportNarrative 行存的是报告“航向”原值。ROT 负值=左转(P)。rudderDeg 负值=左舵。\n")
        f.write("# 同一时刻可能有多行（正文/VDR/AIS 并存），不要自行取舍；位置为空表示报告未给经纬度。\n")
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for p in sorted(points, key=lambda p: (p["vesselId"], p["time"]["utc"], p["provenance"])):
            loc = p.get("location") or {}
            s = p.get("source") or {}
            w.writerow({
                "vesselId": p["vesselId"], "timeBeijing": p["time"]["beijing"], "timeUtc": p["time"]["utc"],
                "approximate": p["time"].get("approximate"), "latDeg": loc.get("latDeg"), "lonDeg": loc.get("lonDeg"),
                "cogDeg": p.get("courseDeg"), "sogKn": p.get("speedKn"), "hdgDeg": p.get("hdgDeg"),
                "rotDegPerMin": p.get("rotDegPerMin"), "stwKn": p.get("stwKn"), "rudderDeg": p.get("rudderDeg"),
                "propellerRpm": p.get("propellerRpm"), "positionText": p.get("positionText"), "provenance": p["provenance"],
                "page": s.get("page"), "pdfPage": s.get("pdfPage"), "line": s.get("line"), "figure": s.get("figure"),
                "figureReading": s.get("figureReading"), "quote": s.get("quote"), "note": p.get("note"),
            })


def main():
    env = environment()
    dc = damage_and_collision()
    case = {
        "schemaVersion": "1.0.0",
        "caseId": "CJK-2024-1230-YangZe22-VegaDream",
        "title": "长江口深水航道“12·30”“YANGZE 22”轮与“VEGA DREAM”轮碰撞事故",
        "accidentType": "碰撞", "accidentGrade": "较大",
        "isFictionalDemo": False, "isPublicReport": True,
        "incidentTimeBeijing": "2024-12-30T22:01:54+08:00", "incidentTimeUtc": "2024-12-30T14:01:54Z",
        "displayTimeZoneOffsetMinutes": 480,
        "reportClock": "正文为北京时间（UTC+8）；VDR 屏显与 YDK SD 卡图表为 UTC；VTS 截图时钟为北京时间",
        "incidentLocation": LOC_REPORT,
        "incidentLocationText": "长江口深水航道39号灯浮下游进口航道内",
        "investigatingBody": "上海海事局“12·30”事故调查组",
        "reportTitle": "长江口深水航道“12·30”“YANGZE 22”轮与“VEGA DREAM”轮碰撞事故调查报告",
        "reportDate": "2025-04",
        "reportDateSource": src("“12·30”事故调查组2025年4月"),
        "pageMapping": "正文页 N = PDF 第 N+2 页；第1–2页 PDF 为封面与目录；report.txt 行号见 source.line",
        "summary": "2024年12月30日22:01:54（北京时间），出口散货船 YANGZE 22（新加坡籍）在长江口深水航道39号灯浮下游，因操舵水手两次反向执行引航员舵令，"
                   "向左大幅偏转越过航道分隔线侵入进口航道，与进口散货船 VEGA DREAM（日本籍）碰撞，YANGZE 22 右舷第5货舱和1号右燃油舱破损，约171.053吨燃油泄漏；"
                   "无人员伤亡，较大等级。YANGZE 22 负主要责任，VEGA DREAM 负次要责任。",
        "summarySource": src("2024年12月30日约2202时，NEBULA SHIPPING PTE LTD.所属的新加坡籍散货船“YANGZE 22”轮与Mitsui O.S.K. Lines,Ltd.所属的日本籍散货船“VEGA DREAM”轮在长江口深水航道39号灯浮下游水域发生碰撞"),
        "investigationMethods": ["吴淞VTS监控记录", "两船VDR与AIS数据", "现场勘验与水下探摸", "YANGZE 22 舵系统检查与测试", "询问船员和引航员", "管理公司调查"],
        "investigationMethodsSource": src("调查组调取了吴淞VTS监控记录以及“YANGZE 22”轮与“VEGA DREAM”轮的VDR数据、AIS数据；实施了船舶现场勘验和水下探摸；检查和测试了“YANGZE 22”轮的舵系统及相关设备；调查询问了双方船舶相关船员和引航员；"),
        "vessels": vessels(),
        "personnel": personnel(),
        "environment": env,
        "collision": dc["collision"],
        "hullDamage": dc["hullDamage"],
        "steeringInvestigation": {
            "checks": ["报警记录与报警测试正常", "No.1/No.2 在 FU/NFU/OVERRIDE 下转向控制正常", "6个舵角指示器同步跟踪",
                       "手轮至MCU线路正常", "舵令与反馈方向正确", "反向报警测试正常", "VDR 舵角信号连接正常", "液压锁报警正常", "舵机间设备正常"],
            "conclusion": "事故前操舵系统工况正常（排除设备故障）",
            "source": src("经综合分析，认定事故发生前“YANGZE 22”轮操舵系统工况正常。"),
            "helmFinding": "事故系操舵水手错误执行引航员指令、反向操舵导致",
            "helmSource": src("认定事故的发生系操舵水手错误地执行了引航员指令，反向操舵导致。"),
        },
        "rudderOrders": rudder_table(),
        "consequences": consequences(),
        **causes_liability(),
        "timeline": timeline(),
        "trackPoints": track_points(),
        "discrepancies": discrepancies(),
        "missingData": missing_data(),
        "extractionNotes": [
            "数据全部来自公开调查报告（Mark 确认可直接使用真实数据）。本机用 pdftotext 文本 + PyMuPDF 提取插图后人工读图，未调用任何外部模型。",
            "每条 source.quote 均能在 report.txt 中找到（去掉页脚行和空白后逐字匹配），核对结果见 _quote_checks.json。",
            "图读值（figure + figureReading）的 quote 是图题，数值由人工读图得到；VDR 屏把“°1”“°4”显示成“?”，按碰撞时刻 AIS 位置校核后还原。",
            "报告没写的字段为 null 并在 missingData 说明；多源冲突并存于 discrepancies，不做取舍。",
            "时间同时给北京时间与 UTC；approximate=true 表示报告写“约”。",
        ],
    }
    ecfc = ecfc_data()
    issues = hb.validate_ecfc(ecfc)
    ecfc["validation"] = {"issueCount": len(issues), "errorCount": sum(1 for i in issues if i["isError"]),
                          "warningCount": sum(1 for i in issues if not i["isError"]), "issues": issues}
    if _qsrc.MISSING:
        print("QUOTES NOT FOUND:")
        for q in _qsrc.MISSING:
            print("  ", q)
    write_json(OUT / "case.json", case)
    write_json(OUT / "ecfc.json", ecfc)
    draw_ecfc(ecfc, issues, OUT / "ecfc.png", OUT / "ecfc.svg")
    checks = verify_all(case, ecfc)
    n_ok = sum(1 for c in checks if c["matched"])
    write_json(OUT / "_quote_checks.json", {"method": "report.txt 去掉页脚页码行与全部空白后逐字子串匹配（_qsrc.Locator）",
                                             "total": len(checks), "matched": n_ok,
                                             "passRate": round(n_ok / len(checks), 4) if checks else None,
                                             "figureQuotes": sum(1 for c in checks if c["figure"]),
                                             "checks": checks})
    write_tracks_csv(case["trackPoints"], OUT / "tracks_from_report.csv", "长江口“12·30”YANGZE 22 / VEGA DREAM")
    print("timeline", len(case["timeline"]), "trackPoints", len(case["trackPoints"]),
          "rudderRows", len(case["rudderOrders"]["rows"]))
    print("ecfc nodes", len(ecfc["nodes"]), "edges", len(ecfc["edges"]), "errors", ecfc["validation"]["errorCount"],
          "warnings", ecfc["validation"]["warningCount"])
    for i in issues:
        print(("ERR " if i["isError"] else "WARN"), i["ruleCode"], i["relatedNodeId"] or "", i["message"])
    print(f"quotes {n_ok}/{len(checks)}")
    return 0 if not _qsrc.MISSING else 1


if __name__ == "__main__":
    sys.exit(main())
