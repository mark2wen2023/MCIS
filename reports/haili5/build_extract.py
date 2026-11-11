# -*- coding: utf-8 -*-
"""Build Haili5 case.json, ecfc.json, validation, and ECFC figure."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from copy import deepcopy

sys.path.insert(0, str(Path(__file__).parent))
from _helpers import geo, src, bt, dm_to_dd, dms_to_dd

OUT = Path(__file__).parent
CLEAN = OUT / "_report_clean.txt"

def ev(eid, time, vessel, desc, category, source, location=None, cog=None, sog=None, extra=None):
    item = {
        "id": eid,
        "time": time,
        "vesselId": vessel,
        "description": desc,
        "category": category,  # 操作/设备/通信/位置/后果/认定
        "location": location,
        "courseDeg": cog,
        "speedKn": sog,
        "source": source,
    }
    if extra:
        item.update(extra)
    return item

def tp(tid, time, vessel, location, cog, sog, source, note=None):
    item = {
        "id": tid,
        "time": time,
        "vesselId": vessel,
        "location": location,
        "courseDeg": cog,
        "speedKn": sog,
        "provenance": "ReportNarrative" if not (source.get("figure")) else "ReportFigure",
        "source": source,
    }
    if note:
        item["note"] = note
    return item

# ---- page map: official page N = PDF page N+5 (body); 简介 is PDF 2-3
def case_data():
    loc_inc = geo(22, 16.71, 113, 48.41)
    loc_h5_col = geo(22, 16.74, 113, 48.37)
    loc_a17_col = geo(22, 16.66, 113, 48.42)

    vessels = [
        {
            "vesselId": "haili5",
            "name": "HAI LI 5",
            "nameCn": "海力5",
            "mmsi": "412356350",
            "mmsiSource": src(23, "MMSI: 412356350", 28, "图18",
                               "仅出现在事发前广州VTS雷达截图的AIS信息框，船舶概况表未列MMSI"),
            "imoNumber": None,
            "chineseShipId": "CN20078835230",
            "callSign": "BHYU",
            "callSignSource": src(23, "呼号: BHYU", 28, "图18",
                                  "仅出现在图18 AIS信息框，船舶概况表未列呼号"),
            "flagState": "中国",
            "portOfRegistry": "南京",
            "vesselType": "散货船",
            "vesselTypeCode": "BulkCarrier",
            "hullMaterial": "钢质",
            "navigationArea": "近海航区",
            "grossTonnage": 8317,
            "netTonnage": 4657,
            "referenceDeadweightT": 13582,
            "loaM": 133.20,
            "beamM": 22.00,
            "moldedDepthM": 9.60,
            "mainEnginePowerKw": 2941.0,
            "builtDate": "2008-06-06",
            "builder": "南京航顺船舶修造厂",
            "owner": "南京海力海运有限公司",
            "ownerAddress": "南京市高淳区阳江镇东湖新村72号",
            "manager": "唐山言鼎海运有限公司",
            "operator": "南京海力海运有限公司",
            "cargo": "型钢11728吨",
            "draftForeM": 6.7,
            "draftAftM": 7.1,
            "aisDraftM": 7.2,
            "aisDraftSource": src(23, "吃水: 7.2米", 28, "图18"),
            "crewOnBoard": 15,
            "pilotOnBoard": False,
            "voyage": {
                "from": "广州番禺龙沙码头",
                "to": "上海",
                "departureBeijing": bt(13, 25, approx=True),
                "aisDestinationInVtsSnapshot": "GUANGZHOU",
                "aisEtaInVtsSnapshot": "2025-10-25 21:00（图18，与计划驶往上海不符，疑似AIS目的港未更新）",
            },
            "certificates": {
                "inspection": "江苏省交通运输综合行政执法监督局2025年4月13日在上海年度检验，2025年5月30日远程临时检验；《国内航行海船安全与环保证书》有效期至2028年6月5日，证书齐全有效",
                "lastFsc": "2025年10月22日在广州番禺船旗国监督检查（2025年入沪船舶专项安检），发现7项缺陷，均已复查纠正",
            },
            "source": src(2, "表1：“海力5”轮船舶概况 船名 海力5 船籍港 南京 船舶识别码 CN20078835230 船舶种类 散货船 总吨 8317 净吨 4657 参考载货量 13582 吨 总长 133.20 米 型宽 22.00 米 型深 9.60 米", 7),
            "sourceContinued": src(3, "船舶建造厂 南京航顺船舶修造厂 船舶管理公司 唐山言鼎海运有限公司 船舶所有人 南京海力海运有限公司", 8),
            "voyageSource": src(6, "该轮事故航次从广州番禺龙沙码头驶往上海。事故发生时该轮装载型钢11728 吨，艏吃水约6.7 米，艉吃水约7.1 米。", 11),
            "crewSource": src(7, "事故航次，该轮在船船员15 人，均持有有效船员适任证书", 12),
            "notes": [
                "国内航行船舶，概况表未列IMO号；图18 AIS信息框IMO为0",
                "图18 AIS船长显示133.0米，与证书总长133.20米略有差别",
            ],
        },
        {
            "vesselId": "wanhai_a17",
            "name": "WAN HAI A17",
            "nameCn": "WAN HAI A17",
            "mmsi": "563234300",
            "mmsiSource": src(23, "563234300", 28, "图18",
                              "仅出现在事发前广州VTS雷达截图的AIS信息框，船舶概况表未列MMSI"),
            "imoNumber": "9968528",
            "chineseShipId": None,
            "callSign": "9V8938",
            "flagState": "新加坡",
            "portOfRegistry": "新加坡",
            "vesselType": "集装箱船",
            "vesselTypeCode": "ContainerShip",
            "hullMaterial": "钢质",
            "navigationArea": "无限航区",
            "grossTonnage": 122045,
            "netTonnage": 79701,
            "referenceDeadweightT": None,
            "loaM": 334.96,
            "beamM": 51.00,
            "moldedDepthM": 20.32,
            "mainEnginePowerKw": 37800.0,
            "builtDate": "2024-08-26",
            "builder": "SAMSUNG HEAVY INDUSTRIES CO.,LTD. KOREA, REPUBLIC OF",
            "owner": "WAN HAI LINES (SINGAPORE) PTE LTD.",
            "ownerAddress": "WAN HAI LINES (SINGAPORE) PTE LTD 79 ANSON ROAD #10-01",
            "manager": "WAN HAI LINES (SINGAPORE) PTE LTD.",
            "operator": "WAN HAI LINES (SINGAPORE) PTE LTD.",
            "cargo": "3962个集装箱",
            "draftForeM": 11.9,
            "draftAftM": 12.4,
            "aisDraftM": 12.7,
            "aisDraftSource": src(23, "吃水: 12.7米", 28, "图18",
                                  "AIS框显示12.7米，正文事故发生时艏吃水11.9米、艉吃水12.4米，二者不完全一致"),
            "crewOnBoard": 23,
            "pilotOnBoard": True,
            "pilot": {
                "name": "梁某林",
                "grade": "海港一级引航员",
                "certificateIssuer": "广州海事局",
                "certificateValidTo": "2026-08-02",
                "boarding": "2025-10-25约1900时在桂山上引航员，计划于2200时靠泊南沙三期码头",
                "source": src(9, "引航员梁某林，男，广东湛江人，持有广州海事局签发的海港一级引航员适任证书，有效期至2026 年8 月2 日。事发时在驾驶台引领船舶进港。", 14),
            },
            "voyage": {
                "from": "宁波",
                "to": "广州南沙（南沙三期码头）",
                "departureBeijing": None,
                "aisDestinationInVtsSnapshot": "CNNSS",
                "aisEtaInVtsSnapshot": "图18 AIS框显示“10月25日10时00分”（数字略密，小时首位更像1；正文计划2200时靠泊，该字段存疑）",
            },
            "certificates": {
                "inspection": "2025年7月16日在深圳蛇口由美国船级社年度检验；《货船设备安全证书》《货船构造安全证书》《国际载重线证书》等有效期至2029年8月25日，证书齐全有效",
                "lastPsc": "2025年9月11日在深圳港港口国监督检查，发现3项缺陷，均已复查纠正",
                "smc": "美国船级社2024年12月1日签发SMC，有效期至2029年11月30日",
                "doc": "美国船级社2023年6月7日签发《符合证明》，适用其他货船（集装箱船），有效期至2028年6月30日",
            },
            "source": src(3, "表2：“WAN HAI A17”轮船舶概况 船名 WAN HAI A17 船籍港 新加坡 IMO 号 9968528 呼号 9V8938 船舶种类 集装箱船", 8),
            "sourceContinued": src(4, "总吨 122045 净吨 79701 总长 334.96 米 型宽 51.00 米 型深 20.32 米 主机功率 37800.0 千瓦 船舶建成日期 2024 年8 月26 日", 9),
            "voyageSource": src(7, "该轮事故航次从宁波驶往广州南沙。该轮装载3962 个集装箱，事故发生时艏吃水11.9 米，艉吃水12.4 米。", 12),
            "crewSource": src(9, "事故航次该轮在船船员23 人，均持有有效船员适任证书和船旗国承认签证", 14),
            "notes": [
                "图18 AIS船长显示335.0米，与证书总长334.96米一致（圆整）",
                "呼号在概况表与图18均为9V8938，互相印证",
            ],
        },
    ]

    environment = {
        "narrativeAtIncident": {
            "weather": "晴到多云",
            "weatherPresetId": "PartlyCloudy",
            "visibilityDescription": "能见度良好",
            "visibilityNm": None,
            "windFrom": "东北",
            "windFromDirDeg": 45,
            "windBeaufort": 4,
            "windSpeedMps": None,
            "windSpeedNote": "报告仅写东北风4级，未给风速数值；蒲福4级约5.5–7.9 m/s，仿真时勿当作精确实测",
            "seaState": "轻浪",
            "waveSignificantHeightM": 0.5,
            "tidePhase": "涨潮",
            "tideHeightM": 2.0,
            "tideHeightNote": "正文写潮高约2m；与图16在19:54处于16:32–23:00涨潮段、由127cm涨向244cm的插值约1.9m相符（基准面为理论深度基准面）",
            "currentType": "涨潮流",
            "currentToDir": "偏北",
            "currentToDirDeg": 0,
            "currentSpeedKn": 1.7,
            "source": src(21, "事发前事发水域晴到多云，能见度良好，东北风4 级，轻浪，浪高约0.5 米，涨潮，潮高约2m，涨潮流，流向偏北，流速约1.7 节。", 26),
        },
        "tideStation": {
            "name": "桂山岛/桂山水域",
            "date": "2025-10-25",
            "lunar": "农历九月初五",
            "tideType": "小潮",
            "datum": "潮高基准面在平均海面下140cm，采用理论深度基准面",
            "source": src(21, "图16：桂山水域当日潮汐表", 26, "图16"),
            "windows": [
                {"kind": "退潮", "from": "00:00", "to": "06:03"},
                {"kind": "涨潮", "from": "06:03", "to": "12:22"},
                {"kind": "退潮", "from": "12:22", "to": "16:32"},
                {"kind": "涨潮", "from": "16:32", "to": "23:00"},
            ],
            "extrema": [
                {"kind": "干潮", "timeBeijing": "2025-10-25T06:03:00+08:00", "heightCm": 60},
                {"kind": "满潮", "timeBeijing": "2025-10-25T12:22:00+08:00", "heightCm": 159},
                {"kind": "干潮", "timeBeijing": "2025-10-25T16:32:00+08:00", "heightCm": 127},
                {"kind": "满潮", "timeBeijing": "2025-10-25T23:00:00+08:00", "heightCm": 244},
            ],
            "readNote": "潮时与潮高从第21页图16表格读取：06:03/60cm，12:22/159cm，16:32/127cm，23:00/244cm。图表为栅格，未嵌入可选中文字。",
        },
        "waterway": {
            "name": "广州港主航道马友石灯船附近",
            "channelOrientation": "168°30′—348°30′",
            "bottomWidthM": 385,
            "channelDepthM": 17,
            "westChartDepthM": [12, 19],
            "westActualDepthM": [14, 21],
            "eastChartDepthM": [12, 13],
            "eastActualDepthM": [14, 15],
            "hazards": ["航道西侧有马友石礁石和马友石灯船"],
            "nearbyVesselsBeforeIncident": [
                "出口：海力5",
                "进口：正海3（已与海力5安全会遇通过）、WAN HAI A17",
                "东北侧深圳龙鼓西航道：大湾区二号",
                "周围无渔船等其他碍航船舶",
            ],
            "source": src(22, "事发水域位于广州港主航道马友石灯船附近，航道走向168°30´—348°30´，底宽385 米，水深17 米。", 27),
        },
        "timeline": [
            {
                "time": bt(19, 54, 32),
                "weatherPresetId": "PartlyCloudy",
                "visibilityNm": None,
                "visibilityDescription": "能见度良好",
                "windSpeedMps": None,
                "windBeaufort": 4,
                "windFromDirDeg": 45,
                "waveSignificantHeightM": 0.5,
                "currentSpeedKn": 1.7,
                "currentToDirDeg": 0,
                "tideHeightM": 2.0,
                "source": src(21, "事发前事发水域晴到多云，能见度良好，东北风4 级，轻浪，浪高约0.5 米，涨潮，潮高约2m，涨潮流，流向偏北，流速约1.7 节。", 26),
            }
        ],
    }

    # personnel (roles at time of accident)
    personnel = {
        "haili5": [
            {"role": "船长", "name": "蔡某飞", "onDutyAtIncident": "事故发生时在驾驶台指挥船舶", "responsibility": "事故次要责任人", "src": src(7, "船长蔡某飞", 12)},
            {"role": "三副", "name": "周某", "onDutyAtIncident": "事故发生时在驾驶台操舵（接替身体不适的值班水手）", "responsibility": None, "src": src(8, "三副周某", 13)},
            {"role": "值班水手", "name": "翁某", "onDutyAtIncident": "事故发生前因身体不舒服离开驾驶台，由三副接替操舵", "responsibility": None, "src": src(8, "事故发生前因身体不舒服离开驾驶台", 13)},
            {"role": "轮机长", "name": "陈某胜", "onDutyAtIncident": "事故发生时在机舱值班", "responsibility": "事故主要责任人", "src": src(8, "轮机长陈某胜", 13)},
            {"role": "大管轮", "name": "任某海", "onDutyAtIncident": "事故发生时在机舱参与船舶失电后的应急处置工作", "responsibility": None, "src": src(8, "大管轮任某海", 13)},
            {"role": "二管轮", "name": "王某础", "onDutyAtIncident": "事故发生时在机舱参与船舶失电后的应急处置工作", "responsibility": "事故主要责任人", "src": src(8, "二管轮王某础", 13)},
            {"role": "值班机工", "name": "余某", "onDutyAtIncident": "事发时在机舱集控室协助处置船舶失电后的应急处置工作", "responsibility": None, "src": src(9, "值班机工余某", 14)},
            {"role": "值班机工", "name": "焦某", "onDutyAtIncident": "事故发生时在机舱底层协助大管轮启动主机，事故发生后死亡", "responsibility": None, "src": src(9, "事故发生时在机舱底层协助大管轮启动主机，事故发生后死亡", 14)},
            {"role": "水手", "name": "雷某逢", "onDutyAtIncident": "事故发生时在房间休息，事故发生后死亡", "responsibility": None, "src": src(9, "事故发生时在房间休息，事故发生后死亡", 14)},
        ],
        "wanhai_a17": [
            {"role": "船长", "name": "闫某", "onDutyAtIncident": "事发时在驾驶台指挥船舶", "responsibility": "事故次要责任人", "src": src(9, "船长闫某", 14)},
            {"role": "引航员", "name": "梁某林", "onDutyAtIncident": "事发时在驾驶台引领船舶进港", "responsibility": "事故次要责任人", "src": src(9, "事发时在驾驶台引领船舶进港", 14)},
            {"role": "二副", "name": "李某晨", "onDutyAtIncident": "事发时在驾驶台，尚未完成与三副陆某昆之间的交接班", "responsibility": None, "src": src(10, "事发时在驾驶台，尚未完成与三副陆某昆之间的交接班", 15)},
            {"role": "三副（值班驾驶员）", "name": "陆某昆", "onDutyAtIncident": "事发时在驾驶台值班，尚未完成与二副之间的交接班", "responsibility": "事故次要责任人", "src": src(10, "事发时在驾驶台值班，尚未完成与二副之间的交接班", 15)},
            {"role": "值班水手", "name": "田某", "onDutyAtIncident": "事发时已完成与缅甸籍水手Z*Y*M*T交接班，尚未离开驾驶台", "responsibility": None, "src": src(10, "事发时已完成与缅甸籍水手Z*Y*M*T 之间交接班工作，尚未离开驾驶台", 15)},
            {"role": "值班水手（操舵）", "name": "Z*Y*M*T", "nationality": "缅甸", "onDutyAtIncident": "事发时正在操舵", "responsibility": None, "src": src(10, "他于2025 年3 月31 日到该轮任职值班水手，事发时正在操舵。", 15)},
        ],
        "note": "报告对其余船员及部分姓名作了脱敏。第十节另出现水手长郭学群、轮机长陈道群等表述，与事发在船职务表未逐一对应，不自行合并。",
    }

    consequences = {
        "grade": "一般等级水上交通事故",
        "gradeSource": src(1, "根据《水上交通事故统计办法》相关规定，构成一般等级水上交通事故。", 6),
        "haili5": "破损进水沉没；右舷120#肋位附近（NO.1与NO.2货舱之间）不规则破口，高度约3.5m，最大宽度约80cm，破口最高点距主甲板约5m；15人落水，13人获救，2人死亡（机工焦某、水手雷某逢）。报告在损失部分注明“省略部分内容”。",
        "haili5Source": src(40, "事故造成该轮破损进水沉没，船上15 人落水，13 人获救，2 人死亡。（省略部分内容）", 45),
        "breachSource": src(14, "该轮右舷120#肋位附近（NO.1 货舱与NO.2 货舱之间）有一高度约3.5m，最大宽度约80cm 的不规则破口，破口最高点距离主甲板约5m", 19),
        "wanhai_a17": "球鼻艏（约380#至386#肋位，另述船首和377#肋位之间）左右舷船壳板撕裂、弯曲、凹陷、褶皱和破损；艏尖舱进水，水位约12.28米，其他舱室正常。",
        "wanhai_a17Source": src(40, "事故造成该轮船首和377#肋位之间，左舷和右舷球鼻艏船壳板不同程度的弯曲、凹陷、褶皱和破损。", 45),
        "collision": {
            "time": bt(19, 54, 32),
            "location": loc_inc,
            "haili5Ais": loc_h5_col,
            "wanhaiA17Ais": loc_a17_col,
            "haili5HeadingDeg": 133,
            "wanhaiA17HeadingDeg": 348,
            "headingIntersectionDeg": 35,
            "collisionAngleDegRange": [30, 40],
            "contact": "WAN HAI A17球鼻艏与海力5右舷NO.1与NO.2货舱交界/之间",
            "timeSource": src(26, "综上，认定碰撞时间为2025 年10 月25 日1954 时32 秒。", 31),
            "locationSource": src(26, "根据两船的AIS 航向和船位，经作图，确定碰撞地点为22°16´.71N/113°48´.41E。", 31),
            "angleSource": src(27, "碰撞时，“WAN HAI A17”轮航向约348°，“海力5”轮航向约133°，两船航向夹角约35°，结合船员陈述，认定两船碰撞时，碰撞角度约为30 至40 度之间。", 32),
        },
        "sinkingTime": bt(20, 1, approx=True),
        "sinkingSource": src(37, "约2001 时，该轮沉没，15 名船员落水。", 42),
        "omittedContent": "简介、事故概况和损失部分均标注“省略部分内容”；正文页码为第1–58页，页脚为“共61页”，第59–61页未包含在本PDF中。",
    }

    liability = {
        "nature": "双方互有过失的碰撞责任事故",
        "primaryCause": "海力5轮发电机组停车，应急发电机组未能自动启动供电，导致船舶失控，与WAN HAI A17轮形成紧迫危险是事故发生的主要原因",
        "haili5": {"share": "主要责任", "primaryPersons": ["轮机长陈某胜", "二管轮王某础"], "secondaryPersons": ["船长蔡某飞"]},
        "wanhai_a17": {"share": "次要责任", "primaryPersons": [], "secondaryPersons": ["船长闫某", "三副陆某昆", "引航员梁某林"]},
        "directCauses": [
            "海力5发电机组停车，应急发电机未能自动启动供电，导致船舶失控并形成紧迫危险",
            "海力5失控后驾驶台值班人员未及时向附近船舶通报失控动态，贻误避让时机",
            "WAN HAI A17疏忽瞭望，未及早发现海力5全船失电及失控；发现后未尽快了解动态并果断采取最有助于避碰的行动",
        ],
        "indirectCauses": [
            "海力5在发生发电机高温保护停车险情后未排查原因，进出港航行使用低位海底门留下隐患",
            "海力5轮机部门未确保应急电源处于正常状态",
            "WAN HAI A17驾驶台资源管理不当",
        ],
        "source": src(45, "“海力5”轮应负事故主要责任，该轮轮机长和二管轮均是事故主要责任人，船长是事故次要责任人；“WAN HAI A17”轮负事故次要责任，船长、三副和引航员均是事故次要责任人。", 50),
    }

    events = build_events(loc_inc, loc_h5_col, loc_a17_col)
    tracks = build_tracks(loc_inc, loc_h5_col, loc_a17_col)

    case = {
        "schemaVersion": "1.0.0",
        "caseId": "GZ-2025-1025-Haili5-WanHaiA17",
        "title": "广州“10·25”“海力5”轮与“WAN HAI A17”轮碰撞事故",
        "accidentCode": "广州10·25",
        "accidentType": "碰撞",
        "accidentGrade": "一般",
        "isFictionalDemo": False,
        "incidentTimeBeijing": "2025-10-25T19:54:32+08:00",
        "incidentTimeUtc": "2025-10-25T11:54:32Z",
        "displayTimeZoneOffsetMinutes": 480,
        "incidentLocation": loc_inc,
        "incidentLocationText": "广州港主航道马友石灯船东北侧水域",
        "investigatingBody": "广州“10·25”事故调查组（广东海事局提级调查）",
        "reportTitle": "广州“10·25”“海力5”轮与“WAN HAI A17”轮碰撞事故调查报告",
        "reportDate": "2026年2月",
        "summary": "2025年10月25日19:54:32（北京时间），南京海力海运有限公司所属散货船“海力5”轮与新加坡万海航运所属集装箱船“WAN HAI A17”轮在广州港主航道马友石灯船东北侧水域发生碰撞。海力5在会遇前全船失电失控并向左偏转进入进口航路；碰撞后海力5沉没，15人落水，13人获救、2人死亡；WAN HAI A17球鼻艏破损。调查认定为双方互有过失的碰撞责任事故，海力5负主要责任。",
        "summarySource": src(1, "2025 年10 月25 日1954 时32 秒，南京海力海运有限公司所属的散货船“海力5”轮与新加坡万海航运股份有限公司所属的“WAN HAI A17”轮在广州港主航道马友石灯船东北侧水域（概位：22°16´.71N/113°48´.41E）发生碰撞", 6),
        "vessels": vessels,
        "environment": environment,
        "personnel": personnel,
        "consequences": consequences,
        "liability": liability,
        "timeline": events,
        "trackPoints": tracks,
        "extractionNotes": [
            "所有时间除另行说明外均为经校对的北京时间（UTC+8）。图23驾驶台CCTV叠字为2025-10-25 11:52:48，与正文19:52:50发现异常相差约2秒，该叠字为UTC。",
            "正文与图24对WAN HAI A17在19:51:15的航向航速不一致（正文348°/9.9节，图24写346°/9.5节、相距约1500米）；两处均予保留并标注来源，不自行取舍。",
            "完整AIS/VDR原始记录未附于报告，仅有叙述性航迹点、碰撞时刻AIS船位和图18瞬时AIS框。",
            "MMSI、海力5呼号仅从图18读出，概况表未列，已单独标注来源。",
            "提取不到的字段为null，未编造排水量、能见度海里数、风速米每秒、NOMOTO参数等。",
        ],
    }
    return case


def build_events(loc_inc, loc_h5_col, loc_a17_col):
    E = []
    def add(*a, **k):
        E.append(ev(*a, **k))

    # --- prior ---
    add("e-20250806-seachest-clean", bt(0, 0, approx=True, day=6, month=8), "haili5",
        "海力5最近一次清洗海底门滤器（2025-08-06，具体钟点未给出）", "设备",
        src(29, "根据船员陈述和该轮的维护保养记录，该轮海底门滤器最近一次清洗是2025 年8 月6 日。", 34))
    add("e-20250922-prior-blackout", bt(17, 0, approx=True, day=22, month=9), "haili5",
        "海力5从珠江口驶往海南避台途中，发电柴油机淡水温度过高（约90℃）导致发电机组停车、全船失电；当时开启右侧低位海底门并用消防泵冲洗甲板，事后未组织清洗海底门滤器", "设备",
        src(29, "2025 年9 月22 日约1700 时，该轮在从珠江口驶往海南避台风过程中，曾发生过发电柴油机淡水温度过高（约90℃），轮机员还未来得及处理就发生了发电机组停车导致全船失电。", 34))
    add("e-emerg-sw-manual", None, "haili5",
        "在广州龙沙码头接岸电前，船员将应急发电机启动开关转至手动；离港前轮机长解除岸电后未转回自动，二管轮开航前未检查开关状态", "设备",
        src(30, "该轮在广州龙沙码头接岸电前，船员将应急发电机启动开关转至手动位置，避免应急发电机自动启动。离港前轮机长值班期间解除岸电，解除岸电后未将应急发电机启动开关转至自动", 35))

    # --- haili5 departure and approach ---
    add("e-h5-depart", bt(13, 25, approx=True), "haili5",
        "海力5装载11728吨型钢从广州番禺龙沙码头开出，计划驶往上海；机舱1号、2号发电机组并联供电", "操作",
        src(30, "2025 年10 月25 日约1325 时，该轮装载11728 吨型钢从广州番禺龙沙码头开出，计划驶往上海。", 35))
    add("e-h5-1600", bt(16, 0), "haili5",
        "海力5沿主航道航行至广州港55#浮附近", "位置",
        src(30, "1600 时，该轮航速9.1 节，航向141°，沿主航道航行至广州港55#浮附近水域，船位22°48´.571N/113°36´.352E。", 35),
        location=geo(22, 48.571, 113, 36.352), cog=141, sog=9.1)
    add("e-h5-1700-pos", bt(17, 0), "haili5",
        "海力5航行至广州港48#浮附近", "位置",
        src(31, "1700 时，该轮航速9.8 节，航向165°，沿主航道航行至广州港48#浮附近水域，船位22°40´.589N/113°41´.104E。", 36),
        location=geo(22, 40.589, 113, 41.104), cog=165, sog=9.8)
    add("e-h5-1700-oiltemp", bt(17, 0, approx=True), "haili5",
        "值班大管轮发现主机滑油温度偏高（77~78℃，未达报警值82℃），晚餐时报告轮机长；主机转速约420–430转。此后大管轮调节滑油调温阀，至事故前温度偏高未有效解决", "设备",
        src(27, "10 月25 日约1700 时，该轮正出港航行，主机转速保持稳定（主机转速在420 至430 转之间），主机滑油温度出现偏高（船员陈述温度为77~78℃，未达到报警值82℃）", 32))
    add("e-h5-1800", bt(18, 0), "haili5",
        "海力5航行至广州港28#浮附近", "位置",
        src(31, "1800 时，该轮航速8.8节，航向162°，沿主航道航行至广州港28#浮附近水域，船位22°31´.03N/113°44´.343E。", 36),
        location=geo(22, 31.03, 113, 44.343), cog=162, sog=8.8)
    add("e-h5-193240-vts", bt(19, 32, 40), "haili5",
        "海力5航行至广州港4号灯浮附近；广州交管中心呼叫提醒注意铜鼓航道出口船舶，海力5回复“收到，不影响，他在我前面走”。此时大管轮与轮机长已完成交接班并讨论主机滑油温度偏高", "通信",
        src(31, "1932 时40 秒，“海力5”轮航行至广州港4 号灯浮附近水域，航向166°，航速7.4 节，广州交管中心呼叫该轮，提醒注意铜鼓航道出口船舶，该轮回复“收到，不影响，他在我前面走”。", 36),
        cog=166, sog=7.4)
    add("e-h5-1942", bt(19, 42), "haili5",
        "WAN HAI A17引航员呼叫海力5，要求尽可能靠右、会红灯；海力5回复“尽量靠右行驶”并继续向右调整航向。两船相距约3.5海里", "通信",
        src(31, "1942 时，该轮船位22°18′.05N/113°48′.07E，航向169°，航速7.2 节，与“WAN HAI A17”轮相距约3.5 海里，“WAN HAI A17”轮引航员呼叫该轮，要求尽可能靠右，会红灯，该轮回复“尽量靠右行驶”", 36),
        location=geo(22, 18.05, 113, 48.07), cog=169, sog=7.2)
    add("e-h5-1945-helm", bt(19, 45), "haili5",
        "值班水手翁某因肚子不舒服离开驾驶台，三副周某接替操舵；海力5沿主航道右舷一侧航行。随后大管轮第二次调节主机滑油调温阀后回到集控室", "操作",
        src(31, "1945 时，该轮航向172°，航速6.7 节，值班水手翁某肚子不舒服去了卫生间，三副周某接替水手操舵。该轮沿主航道右舷一侧航行。", 36),
        cog=172, sog=6.7)

    # blackout and collision - haili5
    add("e-h5-blackout", bt(19, 51, 15), "haili5",
        "1号和2号发电机组突然停止工作，全船失电，主机停车，舵机失灵，随动及非随动操舵均无反应。失电时两船相距约0.8海里。认定依据为港珠澳大桥“西岛岛头北侧”CCTV灯光熄灭", "设备",
        src(32, "1951 时15 秒，该轮船位22°17′.02N/113°48′.25E，航向169°，航速6.5 节，与“WAN HAI A17”轮相距约0.8 海里；此时该轮1 号和2 号发电机组突然停止工作，全船失电，主机停车，舵机失灵", 37),
        location=geo(22, 17.02, 113, 48.25), cog=169, sog=6.5,
        extra={"alsoSource": src(23, "2025 年10 月25 日1951 时15 秒（经校对的北京时间），“海力5”轮驾驶台生活区灯光消失，航行灯熄灭。由此判断此时“海力5”轮发生全船失电。", 28)})
    add("e-h5-blackout-response", bt(19, 51, 15), "haili5",
        "船长立即指令大副和水手长到船首准备应急抛锚，同时给机舱打电话但无人接听；机舱人员在轮机长组织下离开集控室前往启动发电机组；船首开始逐步向左偏转。驾驶台未安排人员前往舵机间手动应急操舵", "操作",
        src(32, "船长立即指令大副和水手长到船首准备应急抛锚，同时给机舱打电话，但机舱无人接听。", 37))
    add("e-h5-195252-vhf", bt(19, 52, 52), "haili5",
        "海力5听到WAN HAI A17呼叫后，通过VHF回应“‘海力5’刚才断电了，让我让我”，随后不断要求对方赶紧避让；船首持续向左偏转。两船相距0.4海里", "通信",
        src(32, "1952 时52 秒，该轮船位22°16′.86N/113°48′.29E，该轮航向163°，航速5.6 节，与“WAN HAI A17”轮相距0.4 海里，听到“WAN HAI A17”轮呼叫后，通过VHF回应“‘海力5’刚才断电了，让我让我”", 37),
        location=geo(22, 16.86, 113, 48.29), cog=163, sog=5.6)
    add("e-h5-195326-vhf", bt(19, 53, 26), "haili5",
        "海力5在甚高频反复大声呼喊“‘海力5’断电，赶快让我让我”，WAN HAI A17回复无法避让；广州交管中心提醒WAN HAI A17对方全船失电、赶紧避让。两船相距约0.3海里", "通信",
        src(32, "1953 时26 秒，该轮航向156°，航速5.1 节，与“WAN HAI A17”轮相距约0.3 海里。该轮在甚高频反复大声呼喊“‘海力5ʼ断电，赶快让我让我”，“WAN HAI A17”轮回复无法避让。", 37),
        cog=156, sog=5.1)
    add("e-h5-1954-yaw", bt(19, 54, 0), "haili5",
        "海力5航向145°、航速4.8节，与WAN HAI A17相距约0.2海里，船首持续向左偏转", "位置",
        src(32, "1954 时，该轮航向145°，航速4.8 节，与“WAN HAI A17”轮相距约0.2 海里，船首持续向左偏转。", 37),
        cog=145, sog=4.8)
    add("e-collision", bt(19, 54, 32), None,
        "两船碰撞：WAN HAI A17球鼻艏与海力5右舷NO.1货舱与NO.2货舱之间部位接触。碰撞后两轮连在一起往偏北方向移动。碰撞地点22°16′.71N/113°48′.41E", "后果",
        src(32, "1954 时32 秒，该轮船位22°16′.74N/113°48′.37E，航向133°，航速4.3 节。该轮右舷NO.1 货舱与NO.2 货舱之间部位与“WAN HAI A17”轮球鼻艏发生碰撞。", 37),
        location=loc_inc, extra={"isPrimaryIncident": True,
            "haili5": {"location": loc_h5_col, "cog": 133, "sog": 4.3},
            "wanhai_a17": {"location": loc_a17_col, "cog": 348, "sog": 9.7}})
    add("e-h5-power-restore", bt(19, 54, 38), "haili5",
        "海力5成功启动1号发电机组并合上主开关，全船恢复供电（CCTV见驾驶台生活区照明灯和航行灯于此时重新亮起）。恢复供电时操舵手柄在右舵，舵叶随后从左舵向右摆动", "设备",
        src(25, "认定“海力5”轮电力恢复时间为2025 年10 月25 日1954 时38 秒。", 30),
        extra={"alsoSource": src(32, "该轮成功启动1 号发电机组，二管轮发现1 号发电机组已经启动且电压和频率稳定，随即合上1 号发电机组主开关，全船恢复供电。", 37)})
    add("e-h5-1955-distress", bt(19, 55, approx=True), "haili5",
        "碰撞后海力5恢复供电，船身向左倾斜进水，被WAN HAI A17持续顶推向北。约1955时三副通过高频向广州交管中心报告两船相撞并请求救助；船长下令全体弃船", "通信",
        src(36, "约1955 时，该轮三副通过高频向广州交管中心报告两船相撞，请求救助", 41))
    add("e-h5-sink", bt(20, 1, approx=True), "haili5",
        "海力5持续进水，海水逐渐漫过生活区甲板，无法释放救生艇，部分船员直接落水或跳水；约2001时该轮沉没，15名船员落水", "后果",
        src(37, "约2001 时，该轮沉没，15 名船员落水。", 42))

    # --- WAN HAI A17 ---
    add("e-a17-pilot", bt(19, 0, approx=True), "wanhai_a17",
        "WAN HAI A17在桂山上引航员，计划于2200时靠泊南沙三期码头", "操作",
        src(33, "2025 年10 月25 日约1900 时，新加坡籍集装箱船“WAN HAI A17”轮在桂山上引航员，计划于2200 时靠泊南沙三期码头。", 38))
    add("e-a17-1902", bt(19, 2, approx=True), "wanhai_a17",
        "行驶至第三分隔带端口，航向358°、航速10.3节，HALF AHEAD，向交管中心报告引航员登轮，随后车钟加至FULL AHEAD", "操作",
        src(33, "1902 时左右，该轮行驶至第三分隔带端口，航向358°，航速10.3 节，HALF AHEAD，该轮向交管中心报告引航员登轮。随后车钟加至FULL AHEAD。", 38),
        cog=358, sog=10.3)
    add("e-a17-1920-abandon-overtake", bt(19, 20, 6), "wanhai_a17",
        "该轮多次联系前方计划进铜鼓航道的“正海3”轮请求把绿浮放左舷通过或加点车被拒后，于1920时06秒放弃追越，减车至SLOW AHEAD；1921时19秒再减至DEAD SLOW AHEAD", "操作",
        src(33, "1920 时06 秒，该轮放弃追越，减车至SLOW AHEAD。", 38))
    add("e-a17-193402", bt(19, 34, 2), "wanhai_a17",
        "WAN HAI A17加车至SLOW AHEAD", "操作",
        src(33, "1934 时02 秒，该轮加车至SLOW AHEAD，航向346°，航速10.4 节。", 38),
        cog=346, sog=10.4)
    add("e-a17-1938", bt(19, 38), "wanhai_a17",
        "航行至广州港定线制1号灯浮，减车至DEAD SLOW AHEAD", "位置",
        src(33, "1938 时，该轮航行至广州港定线制1 号灯浮，航向343°，航速11.2 节，该轮减车至DEAD SLOW AHEAD。", 38),
        cog=343, sog=11.2)
    add("e-a17-1942-call", bt(19, 42), "wanhai_a17",
        "航行至广州港A1南侧水域；引航员联系出口船海力5，请求角度大点往右边去，并提醒本轮为大型船舶无法靠右太多，要求会红灯", "通信",
        src(33, "1942 时，该轮航行至广州港A1 南侧水域，航向345°，航速10.2 节，引航员联系出口船“海力5”轮，请求角度大点往右边去", 38),
        cog=345, sog=10.2)
    add("e-a17-195020-handover", bt(19, 50, 20), "wanhai_a17",
        "二副上驾驶台与三副进行交接班；两名驾驶员沟通值班事宜，两名值班水手注意力在操舵上，均未关注前方船舶情况", "操作",
        src(34, "1950 时20 秒，该轮二副上驾驶台与三副进行交接班。", 39))
    add("e-a17-195115", bt(19, 51, 15), "wanhai_a17",
        "WAN HAI A17航行至广州港A3西北侧水域，距海力5约0.8海里；此时海力5全船失电，航行号灯和照明灯全部熄灭", "位置",
        src(34, "1951 时15 秒，该轮航行至广州港A3 西北侧水域，航向348°，航速9.9 节，距“海力5”轮约0.8 海里，此时“海力5”轮全船失电，船舶航行号灯和照明灯全部熄灭。", 39),
        cog=348, sog=9.9,
        extra={"figureConflict": "图24同为1951时15秒，标注航向346°、航速9.5Kn、两船相距约1500米（0.8海里约1482米，距离相符，航向航速与正文不一致）"})
    add("e-a17-195118-whistle", bt(19, 51, 18), "wanhai_a17",
        "船长前往海图室；引航员为提醒前方正海3尽快转向进入铜鼓航道，下令鸣汽笛一长声", "操作",
        src(34, "1951 时18 秒，该轮船长前往海图室。为提醒航道前方“正海3”轮尽快转向进入铜鼓航道并让出主航道，该轮引航员下令鸣汽笛一长声。", 39))
    add("e-a17-195208-binoculars", bt(19, 52, 8), "wanhai_a17",
        "船长于1951时55秒返回驾驶室操纵台附近，1952时08秒拿起望远镜对前方观察，但未发现海力5全船失电失控；期间引航员使用手机、多次抬头观察，亦未发现异常", "操作",
        src(34, "1951 时55 秒，该轮船长返回驾驶室操纵台附近，并于1952 时08 秒拿起望远镜对前方进行观察，但未发现“海力5”轮全船失电失控的异常情况。", 39))
    add("e-a17-195236-whistle2", bt(19, 52, 36), "wanhai_a17",
        "引航员为提醒前方正海3，再次下令鸣汽笛一长声", "操作",
        src(34, "1952 时36 秒，该轮引航员为提醒前方“正海3”轮，再次下令鸣汽笛一长声。", 39))
    add("e-a17-195250-detect", bt(19, 52, 50), "wanhai_a17",
        "引航员发现海力5异常，问船长“这艘船没点灯，怎么回事？”，随即呼叫“‘海力5’号，怎么回事，你失控了，撞我船头？”。此时两船相距约0.4海里（图24作约740米）", "通信",
        src(34, "1952 时50 秒，该轮引航员发现“海力5”异常，问船长“这艘船没点灯，怎么回事？”，随即呼叫：“‘海力5ʼ号，怎么回事，你失控了，撞我船头？”此时，两船相距约0.4 海里。", 39),
        extra={"cctvUtc": "图23驾驶台侧翼CCTV叠字2025-10-25 11:52:48（UTC），与发现时刻相近"})
    add("e-a17-1953-vhf", bt(19, 53, 0), "wanhai_a17",
        "引航员不断通过VHF09频道呼叫海力5问其动态；海力5回复“让我、让我”；该轮随后回复“无法避让”。交管中心提醒对方全船失电、赶紧避让", "通信",
        src(35, "1953 时，该轮航向347°，航速9.8 节，引航员不断通过VHF09 频道呼叫“海力5”轮问其动态", 40),
        cog=347, sog=9.8)
    add("e-a17-helm-conflict", bt(19, 53, 30, approx=True), "wanhai_a17",
        "1953～1954时，船长先下令往右转，引航员说“我敢往右转吗？”；船长下令往左转，引航员说“不不不”；船长下令左满舵，舵未到左满舵时引航员下令右舵，船长说“右舵就右满舵”；舵刚到右满舵，引航员下令停车，随后船长再下令左满舵并执行，引航员又下令正舵。期间引航员在VHF09多次呼叫交管称海力5失控横越船头", "操作",
        src(35, "1953～1954 时，船长先下令往右转，引航员说“我敢往右转吗？”随后船长下令往左转，引航员说“不不不”，船长下令左满舵", 40))
    add("e-a17-1954-stop", bt(19, 54, 0), "wanhai_a17",
        "WAN HAI A17停车。调查认定：碰撞时该轮航速、航向未发生明显变化", "操作",
        src(35, "1954 时，该轮停车。", 40))
    add("e-a17-195436-report", bt(19, 54, 36), "wanhai_a17",
        "该轮正舵，引航员向交管中心报告发生碰撞、需要赶紧救人，之后开始施救", "通信",
        src(36, "1954 时36 秒，该轮正舵，引航员向交管中心报告发生碰撞，需要赶紧救人，之后该轮开始施救。", 41))
    add("e-a17-astern", bt(19, 55), "wanhai_a17",
        "1955时航速8节，船长下令倒车减速，后切换至“后退二”，持续约2分钟，船速降至约3节；1957时停车，发现海力5在左舷下方即将沉没，下令倒车并开启前侧推；约1958时在离沉船约50米处停住；确认艏尖舱进水（水位约12.28米），其他舱室正常", "操作",
        src(37, "25 日1955 时，该轮航速8 节，船长下令倒车减速，后切换至“后退二”，持续约2 分钟，船速降至约3 节。", 42),
        sog=8)
    add("e-a17-1959-muster", bt(19, 59, approx=True), "wanhai_a17",
        "该轮拉响全船紧急集合警报并广播；通知二副准备释放左舷救助艇，三副向左舷外投放1个SART，大副在船头抛投3个救生圈", "操作",
        src(37, "约1959 时，该轮拉响全船紧急集合警报并广播", 42))
    add("e-rescue-boats", bt(21, 25, approx=True), None,
        "搜救力量陆续救起13人：约2125时“广州港引航6号”救起2人，约2131时“立诚528”救起4人，约2136时“珠海水警129”救起5人，约2146时“广州港引航5号”救起2人。2名失踪人员遗体于2025年12月12日03:24和13:50在打捞现场发现", "后果",
        src(38, "约2125 时，“广州港引航6 号”轮救起2 人。", 43))

    # determination events (causal findings as dated facts already covered; add formal findings as 认定)
    add("e-finding-blackout-cause", None, "haili5",
        "调查认定：正在使用的右侧低位海底门滤器堵塞，冷却海水供应不足，最终冷却淡水温度过高致使两台发电柴油机停车。打捞发现的变形滤器因破坏严重，无法判断是否为当时使用的右舷低位海底门部件（部分推定）", "认定",
        src(30, "最终冷却淡水温度过高致使两台发电柴油机停车。", 35))
    return E


def build_tracks(loc_inc, loc_h5_col, loc_a17_col):
    T = []
    def add(*a, **k):
        T.append(tp(*a, **k))

    add("t-h5-1600", bt(16, 0), "haili5", geo(22, 48.571, 113, 36.352), 141, 9.1,
        src(30, "1600 时，该轮航速9.1 节，航向141°，沿主航道航行至广州港55#浮附近水域，船位22°48´.571N/113°36´.352E。", 35))
    add("t-h5-1700", bt(17, 0), "haili5", geo(22, 40.589, 113, 41.104), 165, 9.8,
        src(31, "1700 时，该轮航速9.8 节，航向165°，沿主航道航行至广州港48#浮附近水域，船位22°40´.589N/113°41´.104E。", 36))
    add("t-h5-1800", bt(18, 0), "haili5", geo(22, 31.03, 113, 44.343), 162, 8.8,
        src(31, "1800 时，该轮航速8.8节，航向162°，沿主航道航行至广州港28#浮附近水域，船位22°31´.03N/113°44´.343E。", 36))
    add("t-h5-193240", bt(19, 32, 40), "haili5", None, 166, 7.4,
        src(31, "1932 时40 秒，“海力5”轮航行至广州港4 号灯浮附近水域，航向166°，航速7.4 节", 36),
        note="仅有概位描述（4号灯浮附近），无经纬度")
    add("t-h5-1942", bt(19, 42), "haili5", geo(22, 18.05, 113, 48.07), 169, 7.2,
        src(31, "1942 时，该轮船位22°18′.05N/113°48′.07E，航向169°，航速7.2 节，与“WAN HAI A17”轮相距约3.5 海里", 36))
    add("t-h5-1945", bt(19, 45), "haili5", None, 172, 6.7,
        src(31, "1945 时，该轮航向172°，航速6.7 节", 36))
    add("t-h5-1948", bt(19, 48), "haili5", None, 174, 6.6,
        src(36, "1948时，航向174°，航速6.6Kn", 41, "图24"),
        note="仅见图24事故经过图标注，正文未列该时刻")
    add("t-h5-1949", bt(19, 49), "haili5", None, 172, 6.5,
        src(36, "1949时，航向172°，航速6.5Kn", 41, "图24"),
        note="仅见图24")
    add("t-h5-195115", bt(19, 51, 15), "haili5", geo(22, 17.02, 113, 48.25), 169, 6.5,
        src(31, "1951 时15 秒，该轮船位22°17′.02N/113°48′.25E，航向169°，航速6.5 节，与“WAN HAI A17”轮相距约0.8 海里", 36))
    add("t-h5-1952", bt(19, 52), "haili5", None, 168, 6.1,
        src(36, "1952时，航向168°，航速6.1Kn", 41, "图24"),
        note="仅见图24")
    add("t-h5-195252", bt(19, 52, 52), "haili5", geo(22, 16.86, 113, 48.29), 163, 5.6,
        src(32, "1952 时52 秒，该轮船位22°16′.86N/113°48′.29E，该轮航向163°，航速5.6 节", 37))
    add("t-h5-195308-vts", bt(19, 53, 8), "haili5",
        geo(22, 16, 113, 48, 50.640, 17.760), 161.0, 5.6,
        src(23, "航速: 5.6节 航向: 161.0度 经纬度: 22° 16′ 50.640″ N 113° 48′ 17.760″ E", 28, "图18"),
        note="图18 VTS截图时钟19:53:08的AIS瞬时值，与前后正文点连续")
    add("t-h5-195326", bt(19, 53, 26), "haili5", None, 156, 5.1,
        src(32, "1953 时26 秒，该轮航向156°，航速5.1 节，与“WAN HAI A17”轮相距约0.3 海里", 37))
    add("t-h5-195400", bt(19, 54, 0), "haili5", None, 145, 4.8,
        src(32, "1954 时，该轮航向145°，航速4.8 节，与“WAN HAI A17”轮相距约0.2 海里", 37))
    add("t-h5-195432", bt(19, 54, 32), "haili5", loc_h5_col, 133, 4.3,
        src(26, "此时“海力5”轮AIS 船位为22°16´.74N/113°48´.37E", 31),
        note="碰撞时刻AIS船位；航向航速见第32页正文")

    add("t-a17-1902", bt(19, 2, approx=True), "wanhai_a17", None, 358, 10.3,
        src(33, "1902 时左右，该轮行驶至第三分隔带端口，航向358°，航速10.3 节", 38))
    add("t-a17-193402", bt(19, 34, 2), "wanhai_a17", None, 346, 10.4,
        src(33, "1934 时02 秒，该轮加车至SLOW AHEAD，航向346°，航速10.4 节。", 38))
    add("t-a17-1938", bt(19, 38), "wanhai_a17", None, 343, 11.2,
        src(33, "1938 时，该轮航行至广州港定线制1 号灯浮，航向343°，航速11.2 节", 38))
    add("t-a17-1942", bt(19, 42), "wanhai_a17", None, 345, 10.2,
        src(33, "1942 时，该轮航行至广州港A1 南侧水域，航向345°，航速10.2 节", 38))
    add("t-a17-1948", bt(19, 48), "wanhai_a17", None, 348, 9.9,
        src(36, "1948时，航向348°，航速9.9Kn", 41, "图24"),
        note="仅见图24")
    add("t-a17-1950", bt(19, 50), "wanhai_a17", None, 348, 9.6,
        src(36, "1950时，航向348°，航速9.6Kn", 41, "图24"),
        note="仅见图24")
    add("t-a17-195115-text", bt(19, 51, 15), "wanhai_a17", None, 348, 9.9,
        src(34, "1951 时15 秒，该轮航行至广州港A3 西北侧水域，航向348°，航速9.9 节，距“海力5”轮约0.8 海里", 39),
        note="正文值；与图24同时刻标注冲突，见下一条")
    add("t-a17-195115-fig24", bt(19, 51, 15), "wanhai_a17", None, 346, 9.5,
        src(36, "1951时15秒，两船相距约1500米 航向346°，航速9.5Kn", 41, "图24"),
        note="图24值；与正文348°/9.9节冲突，距离约1500米与正文0.8海里相符")
    add("t-a17-1952", bt(19, 52), "wanhai_a17", None, 348, 9.6,
        src(36, "1952时，航向348°，航速9.6Kn", 41, "图24"),
        note="仅见图24")
    add("t-a17-1953", bt(19, 53), "wanhai_a17", None, 347, 9.8,
        src(35, "1953 时，该轮航向347°，航速9.8 节", 40))
    add("t-a17-195308-vts", bt(19, 53, 8), "wanhai_a17",
        geo(22, 16, 113, 48, 25.026, 28.758), 347.6, 9.7,
        src(23, "9.7节 航向: 347.6度 22° 16′ 25.026″ N 113° 48′ 28.758″ E", 28, "图18"),
        note="图18 VTS截图时钟19:53:08的AIS瞬时值")
    add("t-a17-1954-fig24", bt(19, 54), "wanhai_a17", None, 347, 9.7,
        src(36, "1954时，两船相距约170米，航向347°，航速9.7Kn", 41, "图24"),
        note="图24；正文1954时仅写停车，未给该时刻航向航速")
    add("t-a17-195432", bt(19, 54, 32), "wanhai_a17", loc_a17_col, 348, 9.7,
        src(26, "“WAN HAI A17”轮AIS 船位为22°16´.66N/113°48´.42E。", 31),
        note="碰撞时刻AIS船位；航向航速见第36页：航向348°，航速9.7节")
    return T



def node(nid, kind, text, lane, time=None, end=None, incident=False, presumptive=False,
         vessel=None, quantities=None, evidence=None, cause_role=None, source=None, layout=None):
    return {
        "nodeId": nid,
        "kind": kind,  # Event | Condition
        "text": text,
        "time": time,
        "endTime": end,
        "lane": lane,
        "isPrimaryIncident": incident,
        "isPresumptive": presumptive,
        "actorVesselId": vessel,
        "quantities": quantities or {},
        "evidenceIds": evidence or [],
        "causeRole": cause_role,  # direct / indirect / consequence / context / none
        "source": source,
        "layoutHint": layout,
    }


def edge(eid, frm, to, kind, bold=False):
    return {"edgeId": eid, "from": frm, "to": to, "kind": kind, "isPrimarySequenceBold": bold}


def ecfc_data():
    nodes = [
        # ---- main sequence lane 0 ----
        node("E01", "Event", "海力5发电柴油机高温停车致全船失电", 0,
             time=bt(19, 51, 15), vessel="haili5",
             quantities={"相距": "约0.8海里", "航向": "169°", "航速": "6.5节"},
             cause_role="direct",
             source=src(32, "此时该轮1 号和2 号发电机组突然停止工作，全船失电，主机停车，舵机失灵", 37),
             layout=(0, 0)),
        node("E02", "Event", "海力5舵机失灵后船首向左偏转", 0,
             time=bt(19, 52, 0, approx=True), vessel="haili5",
             quantities={"1952:52航向": "163°", "航速": "5.6节"},
             cause_role="direct",
             source=src(32, "该轮船首开始逐步向左偏转。", 37),
             layout=(1, 0)),
        node("E03", "Event", "海力5偏转入进口航路形成紧迫危险", 0,
             time=bt(19, 53, 26), vessel="haili5",
             quantities={"相距": "约0.3海里", "航向": "156°"},
             cause_role="direct",
             source=src(41, "该轮失电时，两船相距0.8 海里，随后开始向左偏转进入进口航路与沿航道进港的“WAN HAI A17”轮形成紧迫危险。", 46),
             layout=(2, 0)),
        node("E04", "Event", "两船在马友石灯船东北侧发生碰撞", 0,
             time=bt(19, 54, 32), vessel=None, incident=True,
             quantities={"地点": "22°16.71′N/113°48.41′E", "夹角": "约35°", "碰撞角": "约30–40°",
                         "海力5": "133°/4.3节", "WAN HAI A17": "348°/9.7节"},
             cause_role="direct",
             source=src(26, "认定碰撞时间为2025 年10 月25 日1954 时32 秒。", 31),
             layout=(3, 0)),
        node("E05", "Event", "海力5右舷破口进水并向左倾斜", 0,
             time=bt(19, 54, 40, approx=True), vessel="haili5",
             quantities={"破口": "高约3.5m、最宽约80cm"},
             cause_role="consequence",
             source=src(36, "碰撞事故发生后，该轮恢复供电，船身向左倾斜进水，并被“WAN HAI A17”轮持续顶推向北侧水域移动。", 41),
             layout=(4, 0)),
        node("E06", "Event", "海力5沉没造成15人落水2人死亡", 0,
             time=bt(20, 1, approx=True), vessel="haili5",
             quantities={"落水": "15人", "获救": "13人", "死亡": "2人"},
             cause_role="consequence",
             source=src(37, "约2001 时，该轮沉没，15 名船员落水。", 42),
             layout=(5, 0)),

        # ---- Hai Li 5 machinery / latent (lane +2, +3) ----
        node("E11", "Event", "海力5避台途中发生发电机高温停车", 2,
             time=bt(17, 0, approx=True, day=22, month=9), vessel="haili5",
             quantities={"淡水温度": "约90℃"},
             cause_role="indirect",
             source=src(29, "2025 年9 月22 日约1700 时，该轮在从珠江口驶往海南避台风过程中，曾发生过发电柴油机淡水温度过高（约90℃）", 34),
             layout=(0, 2)),
        node("C11", "Condition", "9月22日失电后未清洗海底门滤器", 2,
             presumptive=False, vessel="haili5", cause_role="indirect",
             source=src(29, "但事后该轮轮机员未组织对海底门滤器进行清洗。", 34),
             layout=(1, 2)),
        node("C12", "Condition", "进出港一直使用右舷低位海底门且富裕水深约2米", 2,
             vessel="haili5", cause_role="indirect",
             source=src(44, "该轮进出广州番禺龙沙码头期间，一直使用低位海底门，航经水域水深最浅处富裕水深约2 米", 49),
             layout=(2, 2)),
        node("C13", "Condition", "右舷低位海底门滤器堵塞", 2,
             presumptive=True, vessel="haili5", cause_role="direct",
             source=src(30, "因此认定，该轮正在使用的右侧低位海底门滤器堵塞，冷却海水供应不足", 35),
             layout=(3, 2),
             quantities={"说明": "调查结论；残骸滤器无法确认为当时在用管路，吸入泥沙加重堵塞属推断"}),
        node("C14", "Condition", "冷却海水供应不足使发电柴油机淡水温度升高", 2,
             vessel="haili5", cause_role="direct",
             source=src(28, "冷却海水供水不足可导致发电柴油机冷却淡水温度快速升高，最终高温保护停车。", 33),
             layout=(4, 2)),
        node("E12", "Event", "大管轮发现主机滑油温度升至77至78℃", 1,
             time=bt(17, 0, approx=True), vessel="haili5",
             quantities={"滑油温度": "77~78℃", "报警值": "82℃"},
             cause_role="indirect",
             source=src(31, "值班轮机员大管轮发现主机滑油温度偏高（77~78℃，尚未达到报警值82℃）", 36),
             layout=(0, 1)),
        node("C15", "Condition", "轮机员注意力集中于主机温度未监控发电机", 1,
             vessel="haili5", cause_role="direct",
             source=src(28, "事故发生前在机舱值班的轮机长和刚交完班的大管轮注意力主要放在主机滑油温度异常升高的处理，均未注意发电机组的参数和报警情况。", 33),
             layout=(1, 1)),

        # emergency generator
        node("E13", "Event", "接岸电时船员将应急发电机开关转至手动", 3,
             time=None, vessel="haili5", cause_role="indirect",
             source=src(30, "该轮在广州龙沙码头接岸电前，船员将应急发电机启动开关转至手动位置", 35),
             layout=(0, 3)),
        node("E14", "Event", "轮机长解除岸电后未将开关转回自动", 3,
             time=None, vessel="haili5", cause_role="indirect",
             source=src(30, "离港前轮机长值班期间解除岸电，解除岸电后未将应急发电机启动开关转至自动", 35),
             layout=(1, 3)),
        node("E15", "Event", "二管轮开航前未检查应急发电机开关", 3,
             time=bt(13, 25, approx=True), vessel="haili5", cause_role="indirect",
             source=src(30, "二管轮负责该轮该航次开航前备车，其在开航前未前往应急发电机间检查应急发电机启动开关状态。", 35),
             layout=(2, 3)),
        node("C16", "Condition", "应急发电机启动开关处于手动模式", 3,
             vessel="haili5", cause_role="direct",
             source=src(15, "发现该轮应急发电机开关处于手动模式。", 20),
             layout=(3, 3)),

        # haili5 bridge response lane +1 right
        node("C17", "Condition", "驾驶台与机舱未能建立有效联系", 1,
             vessel="haili5", cause_role="direct",
             source=src(21, "驾驶台未与机舱建立有效联系，未安排人员前往舵机间进行手动应急操舵。", 26),
             layout=(3, 1)),
        node("E16", "Event", "海力5船长未及时用VHF通报失控", 1,
             time=bt(19, 51, 30, approx=True), vessel="haili5", cause_role="direct",
             source=src(41, "船长没有第一时间通过甚高频播报本船失电、船舶失控并向左偏转的动态", 46),
             layout=(2, 1)),
        node("E17", "Event", "海力5在VHF回应刚断电并要求让路", 1,
             time=bt(19, 52, 52), vessel="haili5", cause_role="direct",
             source=src(32, "通过VHF回应“‘海力5’刚才断电了，让我让我”", 37),
             layout=(4, 1)),
        node("E18", "Event", "机舱启动1号发电机并恢复供电", 1,
             time=bt(19, 54, 38), vessel="haili5", cause_role="consequence",
             source=src(25, "认定“海力5”轮电力恢复时间为2025 年10 月25 日1954 时38 秒。", 30),
             layout=(5, 1)),

        # ---- WAN HAI A17 lanes -1, -2 ----
        node("E21", "Event", "WAN HAI A17在桂山登上引航员沿进口航路进港", -2,
             time=bt(19, 0, approx=True), vessel="wanhai_a17", cause_role="context",
             source=src(33, "约1900 时，新加坡籍集装箱船“WAN HAI A17”轮在桂山上引航员", 38),
             layout=(0, -2)),
        node("E22", "Event", "二副上驾驶台与三副交接班", -1,
             time=bt(19, 50, 20), vessel="wanhai_a17", cause_role="indirect",
             source=src(34, "1950 时20 秒，该轮二副上驾驶台与三副进行交接班。", 39),
             layout=(1, -1)),
        node("C21", "Condition", "驾驶台6人处于交接班且瞭望未有效履行", -1,
             vessel="wanhai_a17", cause_role="indirect",
             source=src(44, "“海力5”轮失电时，该轮驾驶台值班驾驶员和值班水手处于交接班时间，包括船长、引航员在内共有6 人在驾驶台，但瞭望未得到有效履行。", 49),
             layout=(2, -1)),
        node("E23", "Event", "船长赴海图室后用望远镜观察仍未发现失电", -2,
             time=bt(19, 52, 8), vessel="wanhai_a17", cause_role="direct",
             source=src(34, "并于1952 时08 秒拿起望远镜对前方进行观察，但未发现“海力5”轮全船失电失控的异常情况。", 39),
             layout=(2, -2)),
        node("E24", "Event", "引航员两次鸣一长声提醒前方正海3", -2,
             time=bt(19, 51, 18), vessel="wanhai_a17", cause_role="direct",
             source=src(34, "该轮引航员下令鸣汽笛一长声。", 39),
             layout=(1, -2)),
        node("C22", "Condition", "海力5失电后航行灯熄灭增大他船发现难度", -1,
             vessel="haili5", cause_role="direct",
             source=src(41, "客观上增大了“WAN HAI A17”轮发现该轮失控状态及其动态的难度，贻误了“WAN HAI A17”轮采取避让行动的时机。", 46),
             layout=(3, -1)),
        node("E25", "Event", "引航员发现海力5未点灯并呼叫动态", -1,
             time=bt(19, 52, 50), vessel="wanhai_a17",
             quantities={"相距": "约0.4海里", "滞后": "失电后约90秒"},
             cause_role="direct",
             source=src(34, "1952 时50 秒，该轮引航员发现“海力5”异常，问船长“这艘船没点灯，怎么回事？”", 39),
             layout=(4, -1)),
        node("E26", "Event", "船长与引航员交替下达相反舵令", -2,
             time=bt(19, 53, 30, approx=True), vessel="wanhai_a17", cause_role="direct",
             source=src(35, "船长先下令往右转，引航员说“我敢往右转吗？”随后船长下令往左转，引航员说“不不不”", 40),
             layout=(4, -2)),
        node("C23", "Condition", "紧急情况下引航员与船长指挥权不明确", -2,
             vessel="wanhai_a17", cause_role="indirect",
             source=src(45, "在紧急情况下，引航员和船长的指挥权不明确，驾驶台资源管理不当。", 50),
             layout=(3, -2)),
        node("E27", "Event", "WAN HAI A17临近碰撞前停车", -1,
             time=bt(19, 54, 0), vessel="wanhai_a17",
             quantities={"碰撞时航向": "348°", "航速": "9.7节"},
             cause_role="direct",
             source=src(35, "1954 时，该轮停车。", 40),
             layout=(5, -1)),
        node("C24", "Condition", "碰撞时该轮航速航向未发生明显变化", -1,
             vessel="wanhai_a17", cause_role="direct",
             source=src(43, "两船发生碰撞时该轮航速、航向未发生明显变化。", 48),
             layout=(5, -2)),

        # context
        node("C31", "Condition", "两船在主航道进出口对遇", 0,
             # wait, condition cannot be on primary lane per validator!
             # put on lane +4 or -3
             vessel=None, cause_role="context",
             source=src(22, "事发前出口航路附近水域有出口船舶“海力5”轮，进口航路船舶有“正海3”轮和“WAN HAI A17”轮", 27),
             layout=(2, 4)),
        node("C32", "Condition", "能见度良好东北风4级涨潮流偏北约1.7节", -3,
             cause_role="context",
             source=src(21, "事发前事发水域晴到多云，能见度良好，东北风4 级，轻浪，浪高约0.5 米，涨潮，潮高约2m，涨潮流，流向偏北，流速约1.7 节。", 26),
             layout=(3, -3)),
    ]
    # fix C31 lane
    for n in nodes:
        if n["nodeId"] == "C31":
            n["lane"] = 4

    edges = [
        # primary sequence (bold)
        edge("s01", "E01", "E02", "Sequence", True),
        edge("s02", "E02", "E03", "Sequence", True),
        edge("s03", "E03", "E04", "Sequence", True),
        edge("s04", "E04", "E05", "Sequence", True),
        edge("s05", "E05", "E06", "Sequence", True),
        # machinery / latent (no Event->Condition edges)
        edge("i11", "C11", "C13", "Influence"),
        edge("i12", "C12", "C13", "Influence"),
        edge("i13", "C13", "C14", "Influence"),
        edge("i14", "C14", "E01", "Influence"),
        edge("s12", "E11", "E01", "Sequence"),
        edge("s13", "E12", "E01", "Sequence"),
        edge("i15", "C15", "E01", "Influence"),
        # emergency generator -> loss of steering after blackout
        edge("s14", "E13", "E14", "Sequence"),
        edge("s15", "E14", "E15", "Sequence"),
        edge("i16", "C16", "E02", "Influence"),
        edge("s16", "E15", "E02", "Sequence"),
        edge("i17", "C17", "E02", "Influence"),
        # Hai Li 5 bridge comms
        edge("s17", "E01", "E16", "Sequence"),
        edge("i19", "C22", "E25", "Influence"),
        edge("i34", "C22", "E16", "Influence"),
        edge("s18", "E16", "E25", "Sequence"),
        edge("s20", "E02", "E17", "Sequence"),
        edge("s19", "E17", "E03", "Sequence"),
        edge("s21", "E04", "E18", "Sequence"),
        # WAN HAI A17
        edge("s22", "E21", "E22", "Sequence"),
        edge("s23", "E22", "E23", "Sequence"),
        edge("s24", "E22", "E24", "Sequence"),
        edge("i21", "C21", "E23", "Influence"),
        edge("i22", "C21", "E24", "Influence"),
        edge("i33", "C21", "E25", "Influence"),
        edge("s25", "E23", "E25", "Sequence"),
        edge("s26", "E24", "E25", "Sequence"),
        edge("s27", "E25", "E26", "Sequence"),
        edge("s28", "E26", "E27", "Sequence"),
        edge("s29", "E27", "E04", "Sequence"),
        edge("i23", "C23", "E26", "Influence"),
        edge("i24", "C24", "E04", "Influence"),
        edge("i31", "C31", "E03", "Influence"),
        edge("i32", "C32", "E04", "Influence"),
    ]

    # attach evidence ids for non-empty sources
    for n in nodes:
        if n.get("source") and not n["evidenceIds"]:
            page = n["source"].get("page")
            fig = n["source"].get("figure")
            ev = [f"report:p{page}"]
            if fig:
                ev.append(f"report:{fig}")
            n["evidenceIds"] = ev

    return {
        "schemaVersion": "1.0.0",
        "caseId": "GZ-2025-1025-Haili5-WanHaiA17",
        "standard": "论文2.5节 / 表4（Buys 1995, Sklet 2002）；架构4.9节 EcfcValidator",
        "isDraft": True,
        "isFictionalDemo": False,
        "nodes": nodes,
        "edges": edges,
        "liabilityMapping": {
            "primaryCauseNodeIds": ["E01", "C16", "E02", "E03"],
            "directCauseNodeIds": ["E01", "C16", "E02", "E03", "E16", "C22", "C21", "E23", "E24", "E25", "E26", "E27", "C24"],
            "indirectCauseNodeIds": ["E11", "C11", "C12", "E12", "C15", "E13", "E14", "E15", "C21", "C23"],
            "haili5PrimaryResponsibility": "主要责任（发电机组停车且应急发电机未自动启动，导致失控并形成紧迫危险）",
            "wanhaiA17SecondaryResponsibility": "次要责任（疏忽瞭望、未采取最有助于避碰的行动，以及驾驶台资源管理不当）",
        },
        "notes": [
            "主序列从全船失电起笔，向前用次序列和条件倒推，向后写进水沉没。",
            "C13（滤器堵塞）为调查认定，但残骸滤器无法确认为当时在用管路，且“吸入泥沙加重堵塞”为推断，故标为推定节点。",
            "C32环境条件能见度良好，并非碰撞的促成因素，仅作情境条件挂到事故节点。",
        ],
    }




CN_VERBS = ("发生", "停车", "失电", "偏转", "进入", "形成", "碰撞", "进水", "倾斜",
            "沉没", "造成", "发现", "清洗", "使用", "转至", "转回", "检查",
            "通报", "回应", "要求", "启动", "恢复", "登上", "交接", "观察",
            "鸣", "提醒", "呼叫", "下达", "下令", "靠泊", "开出")


def _zh_len(s: str) -> int:
    return len(s or "")


def validate_ecfc(doc: dict) -> list:
    issues = []
    nodes = {n["nodeId"]: n for n in doc["nodes"]}
    edges = doc["edges"]
    idset = set(nodes)

    def err(code, msg, nid=None, eid=None):
        issues.append({"ruleCode": code, "isError": True, "message": msg,
                       "relatedNodeId": nid, "relatedEdgeId": eid})

    def warn(code, msg, nid=None, eid=None):
        issues.append({"ruleCode": code, "isError": False, "message": msg,
                       "relatedNodeId": nid, "relatedEdgeId": eid})

    # dangling refs
    for e in edges:
        if e["from"] not in idset:
            err("ECFC-E00", f"边起点不存在: {e['from']}", eid=e["edgeId"])
        if e["to"] not in idset:
            err("ECFC-E00", f"边终点不存在: {e['to']}", eid=e["edgeId"])

    # edge type vs node type
    for e in edges:
        a, b = nodes.get(e["from"]), nodes.get(e["to"])
        if not a or not b:
            continue
        if a["kind"] == "Event" and b["kind"] == "Condition":
            err("ECFC-E01", "事件不能用实线（或任何边）指向条件；条件应虚线指向事件或条件",
                nid=a["nodeId"], eid=e["edgeId"])
        if a["kind"] == "Condition" and e["kind"] != "Influence":
            err("ECFC-E01", "条件出发的边必须是虚线 Influence", eid=e["edgeId"])
        if a["kind"] == "Event" and b["kind"] == "Event" and e["kind"] != "Sequence":
            err("ECFC-E01", "事件之间应使用实线 Sequence", eid=e["edgeId"])

    # condition on primary lane
    for n in nodes.values():
        if n["kind"] == "Condition" and n["lane"] == 0:
            err("ECFC-E02", "条件节点不得放在主序列（lane=0）", nid=n["nodeId"])

    # incident uniqueness
    incidents = [n for n in nodes.values() if n.get("isPrimaryIncident")]
    if len(incidents) != 1:
        err("ECFC-E03", f"主序列须有且仅有一个事故节点，当前 {len(incidents)} 个")
    elif incidents[0]["lane"] != 0 or incidents[0]["kind"] != "Event":
        err("ECFC-E03", "事故节点必须是主序列上的事件", nid=incidents[0]["nodeId"])

    # primary fork / cycle among lane-0 events
    primary_events = [n["nodeId"] for n in nodes.values() if n["kind"] == "Event" and n["lane"] == 0]
    pe = set(primary_events)
    succ = {i: [] for i in pe}
    pred_count = {i: 0 for i in pe}
    for e in edges:
        if e["from"] in pe and e["to"] in pe and e["kind"] == "Sequence":
            succ[e["from"]].append(e["to"])
            pred_count[e["to"]] += 1
    for nid, outs in succ.items():
        if len(outs) > 1:
            err("ECFC-E04", f"主序列在 {nid} 处分叉", nid=nid)
    if sum(1 for v in pred_count.values() if v > 1) > 0:
        err("ECFC-E04", "主序列出现汇合/分叉（入度>1）")
    # cycle
    seen = set(); stack = set()
    def dfs(u):
        if u in stack:
            return True
        if u in seen:
            return False
        stack.add(u)
        for v in succ.get(u, []):
            if dfs(v):
                return True
        stack.remove(u); seen.add(u)
        return False
    if any(dfs(u) for u in pe):
        err("ECFC-E04", "主序列出现环")

    # warnings
    for n in nodes.values():
        if n["kind"] == "Event":
            if n.get("time") is None:
                warn("ECFC-W02", "事件没有时间", nid=n["nodeId"])
            tl = _zh_len(n["text"])
            if tl > 30:
                warn("ECFC-W03", f"事件文本超过30字（{tl}字）: {n['text']}", nid=n["nodeId"])
            if not any(v in n["text"] for v in CN_VERBS):
                warn("ECFC-W03", f"事件文本可能缺少主动动词: {n['text']}", nid=n["nodeId"])
        if not n.get("isPresumptive") and not n.get("evidenceIds"):
            warn("ECFC-W01", "非推定节点没有关联证据", nid=n["nodeId"])
        if n.get("isPresumptive") and n["kind"] != "Condition" and n["kind"] != "Event":
            warn("ECFC-W00", "推定标记只能用于事件或条件", nid=n["nodeId"])

    # conditions must connect to at least one event (directly or via condition chain)
    from collections import defaultdict
    adj = defaultdict(list)
    for e in edges:
        adj[e["from"]].append(e["to"])

    def reaches_event(start):
        stack = [start]; vis = set()
        while stack:
            u = stack.pop()
            if u in vis:
                continue
            vis.add(u)
            if u != start and nodes.get(u, {}).get("kind") == "Event":
                return True
            for v in adj.get(u, []):
                stack.append(v)
        return False

    for n in nodes.values():
        if n["kind"] == "Condition" and not reaches_event(n["nodeId"]):
            warn("ECFC-W04", "条件没有连到任何事件", nid=n["nodeId"])

    # primary time monotonic
    prim = [n for n in nodes.values() if n["kind"] == "Event" and n["lane"] == 0]
    # order by topology
    roots = [i for i in primary_events if pred_count.get(i, 0) == 0]
    order = []
    if len(roots) == 1:
        u = roots[0]
        while u:
            order.append(u)
            nxt = succ.get(u, [])
            u = nxt[0] if nxt else None
        times = []
        for nid in order:
            t = nodes[nid].get("time")
            if t and t.get("utc"):
                times.append((nid, t["utc"]))
        for (a, ta), (b, tb) in zip(times, times[1:]):
            if tb < ta:
                warn("ECFC-W05", f"主序列时间不单调: {a} {ta} → {b} {tb}", nid=b)

    return issues


def verify_quotes(case: dict, text: str, n_sample=10) -> list:
    """Randomly (but stably) sample events and confirm quote appears in cleaned report (whitespace-insensitive)."""
    import hashlib
    norm = re.sub(r"\s+", "", text)
    candidates = []
    for ev in case["timeline"]:
        q = (ev.get("source") or {}).get("quote") or ""
        fig = (ev.get("source") or {}).get("figure")
        if q and not fig:
            candidates.append(("timeline", ev["id"], ev["source"]["page"], q, ev["description"][:40]))
    for tp in case["trackPoints"]:
        q = (tp.get("source") or {}).get("quote") or ""
        fig = (tp.get("source") or {}).get("figure")
        if q and not fig:
            candidates.append(("track", tp["id"], tp["source"]["page"], q, f"{tp['vesselId']} {tp.get('courseDeg')}/{tp.get('speedKn')}"))
    # stable pick 10 spread across file
    scored = []
    for i, c in enumerate(candidates):
        h = int(hashlib.sha1(c[1].encode()).hexdigest(), 16)
        scored.append((h, i, c))
    scored.sort()
    # take 10 well-spaced by original index
    if len(candidates) <= n_sample:
        picked = candidates
    else:
        step = max(1, len(candidates) // n_sample)
        picked = [candidates[(i * step + 3) % len(candidates)] for i in range(n_sample)]
        # unique
        seen=set(); uniq=[]
        for p in picked:
            if p[1] not in seen:
                uniq.append(p); seen.add(p[1])
        picked = uniq[:n_sample]

    results = []
    for kind, eid, page, quote, label in picked:
        qn = re.sub(r"\s+", "", quote)
        # allow minor punctuation variants ´ vs ′
        variants = {qn, qn.replace("´", "′"), qn.replace("′", "´")}
        ok = any(v and v in norm for v in variants)
        results.append({
            "id": eid, "kind": kind, "page": page, "quote": quote,
            "label": label, "matched": ok,
        })
    return results


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def draw_ecfc(doc: dict, issues: list, outfile: Path, svgfile: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse, Rectangle
    from matplotlib import font_manager
    from matplotlib.lines import Line2D

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    font_bold = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    fp = font_manager.FontProperties(fname=font_path)
    fpb = font_manager.FontProperties(fname=font_bold)
    plt.rcParams["font.family"] = fp.get_name()
    # register
    font_manager.fontManager.addfont(font_path)

    # layout: x from layoutHint col, y from lane
    nodes = doc["nodes"]
    edges = doc["edges"]
    pos = {}
    for n in nodes:
        col, lane = n.get("layoutHint") or (0, n["lane"])
        # lane: + up
        pos[n["nodeId"]] = (col * 3.4, lane * 2.15)

    # auto-spread if overlap
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    xmin, xmax = min(xs) - 2.2, max(xs) + 2.2
    ymin, ymax = min(ys) - 1.8, max(ys) + 2.2

    fig_w = max(18, (xmax - xmin) * 0.85 + 4)
    fig_h = max(11, (ymax - ymin) * 0.85 + 3.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=140)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("#f4f1ea")
    ax.set_facecolor("#f4f1ea")

    # main sequence guideline
    prim = [n for n in nodes if n["kind"] == "Event" and n["lane"] == 0]
    if prim:
        pxs = [pos[n["nodeId"]][0] for n in prim]
        ax.plot([min(pxs)-1.6, max(pxs)+1.6], [0, 0], color="#c8c2b4", lw=8, zorder=0, solid_capstyle="round")

    byid = {n["nodeId"]: n for n in nodes}

    def node_size(n):
        text = n["text"]
        # wrap
        if len(text) <= 12:
            lines = [text]
        elif len(text) <= 22:
            k = len(text) // 2
            lines = [text[:k], text[k:]]
        else:
            k = 11
            lines = [text[i:i+k] for i in range(0, len(text), k)]
        return lines, 2.7, 0.95 + 0.22 * (len(lines) - 1)

    # edges first
    for e in edges:
        if e["from"] not in pos or e["to"] not in pos:
            continue
        x1, y1 = pos[e["from"]]
        x2, y2 = pos[e["to"]]
        a, b = byid[e["from"]], byid[e["to"]]
        _, w1, h1 = node_size(a)
        _, w2, h2 = node_size(b)
        # start/end at box border
        dx, dy = x2 - x1, y2 - y1
        dist = (dx*dx + dy*dy) ** 0.5 or 1
        # shrink
        sx = x1 + dx / dist * (w1 * 0.52)
        sy = y1 + dy / dist * (h1 * 0.62)
        ex = x2 - dx / dist * (w2 * 0.52)
        ey = y2 - dy / dist * (h2 * 0.62)
        bold = e.get("isPrimarySequenceBold")
        if e["kind"] == "Influence":
            style = dict(arrowstyle="-|>", color="#5b4c3a", lw=1.2,
                         connectionstyle="arc3,rad=0.08", linestyle="dashed")
        else:
            style = dict(arrowstyle="-|>", color="#1a1a1a",
                         lw=2.8 if bold else 1.3,
                         connectionstyle="arc3,rad=0.04")
        arr = FancyArrowPatch((sx, sy), (ex, ey), mutation_scale=16 if bold else 12,
                              zorder=2, **style)
        ax.add_patch(arr)

    # nodes
    for n in nodes:
        x, y = pos[n["nodeId"]]
        lines, w, h = node_size(n)
        presum = n.get("isPresumptive")
        incident = n.get("isPrimaryIncident")
        if n["kind"] == "Event":
            fc = "#f4d35e" if incident else "#fff7d6"
            ec = "#8b1e1e" if incident else "#2b2b2b"
            lw = 2.6 if (n["lane"] == 0) else 1.3
            box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                                 boxstyle="square,pad=0.0",
                                 facecolor=fc, edgecolor=ec, linewidth=lw,
                                 linestyle=(0, (3, 2)) if presum else "solid",
                                 zorder=3)
            ax.add_patch(box)
        else:
            fc = "#e8f4ea"
            ec = "#1f4d2e"
            ell = Ellipse((x, y), w * 1.05, h * 1.25,
                          facecolor=fc, edgecolor=ec, linewidth=1.4,
                          linestyle=(0, (3, 2)) if presum else "solid",
                          zorder=3)
            ax.add_patch(ell)
        # text
        body = "\n".join(lines)
        time = n.get("time") or {}
        tlab = ""
        if time.get("beijing"):
            ts = time["beijing"][11:19]
            if time.get("approximate"):
                tlab = "约 " + ts
            else:
                tlab = ts
            # include date if not Oct 25
            if not time["beijing"].startswith("2025-10-25"):
                tlab = time["beijing"][:10] + " " + tlab
        ax.text(x, y + (0.12 if tlab else 0), body, ha="center", va="center",
                fontproperties=fpb if incident or n["lane"] == 0 and n["kind"]=="Event" else fp,
                fontsize=8.2 if incident else 7.6, color="#1a1a1a", zorder=4,
                linespacing=1.15)
        if tlab:
            ax.text(x, y - h/2 + 0.16, tlab, ha="center", va="center",
                    fontproperties=fp, fontsize=6.4, color="#4a4338", zorder=4)
        if presum:
            ax.text(x + w/2 - 0.05, y + h/2 - 0.05, "推定", ha="right", va="top",
                    fontproperties=fp, fontsize=6, color="#8b1e1e", zorder=5)

    # title and legend
    ax.text((xmin+xmax)/2, ymax - 0.35,
            "广州“10·25”海力5 轮与 WAN HAI A17 轮碰撞事故  ECFC 草稿",
            ha="center", va="top", fontproperties=fpb, fontsize=15, color="#1a1a1a")
    ax.text((xmin+xmax)/2, ymax - 0.85,
            "按论文 2.5 节表 4：事件=矩形，条件=椭圆；事件之间实线箭头（主序列加粗），条件用虚线箭头；推定项虚线框。待调查员确认。",
            ha="center", va="top", fontproperties=fp, fontsize=8, color="#4a4338")

    # lane labels
    ax.text(xmin + 0.15, 3 * 2.15, "次序列　应急电源", ha="left", va="center", fontproperties=fp, fontsize=7, color="#555")
    ax.text(xmin + 0.15, 2 * 2.15, "次序列　机电隐患", ha="left", va="center", fontproperties=fp, fontsize=7, color="#555")
    ax.text(xmin + 0.15, 1 * 2.15, "次序列　海力5驾驶台/机舱", ha="left", va="center", fontproperties=fp, fontsize=7, color="#555")
    ax.text(xmin + 0.15, 0.0, "主序列", ha="left", va="center", fontproperties=fpb, fontsize=8, color="#333")
    ax.text(xmin + 0.15, -1 * 2.15, "次序列　WAN HAI A17 驾驶台", ha="left", va="center", fontproperties=fp, fontsize=7, color="#555")
    ax.text(xmin + 0.15, -2 * 2.15, "次序列　瞭望与操舵", ha="left", va="center", fontproperties=fp, fontsize=7, color="#555")

    n_err = sum(1 for i in issues if i["isError"])
    n_warn = sum(1 for i in issues if not i["isError"])
    ax.text(xmin + 0.15, ymin + 0.35,
            f"表4自查：错误 {n_err} 项，警告 {n_warn} 项。非虚构案件（IsFictionalDemo=false）。提取草稿，须对照原文与证据确认后使用。",
            ha="left", va="bottom", fontproperties=fp, fontsize=7.5, color="#3a3328")

    legend_elems = [
        Line2D([0], [0], color="#1a1a1a", lw=2.8, label="主序列事件（加粗实线）"),
        Line2D([0], [0], color="#1a1a1a", lw=1.3, label="事件顺序（实线）"),
        Line2D([0], [0], color="#5b4c3a", lw=1.2, ls="--", label="条件影响（虚线）"),
    ]
    leg = ax.legend(handles=legend_elems, loc="upper right", frameon=True, fontsize=8)
    for t in leg.get_texts():
        t.set_fontproperties(fp)

    fig.tight_layout()
    fig.savefig(outfile, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    fig.savefig(svgfile, format="svg", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print("wrote", outfile, svgfile)


def main():
    case = case_data()
    ecfc = ecfc_data()
    issues = validate_ecfc(ecfc)
    ecfc["validation"] = {
        "issueCount": len(issues),
        "errorCount": sum(1 for i in issues if i["isError"]),
        "warningCount": sum(1 for i in issues if not i["isError"]),
        "issues": issues,
    }
    write_json(OUT / "case.json", case)
    write_json(OUT / "ecfc.json", ecfc)
    draw_ecfc(ecfc, issues, OUT / "ecfc.png", OUT / "ecfc.svg")

    text = CLEAN.read_text(encoding="utf-8")
    checks = verify_quotes(case, text, 10)
    write_json(OUT / "_quote_checks.json", checks)
    print("timeline events", len(case["timeline"]))
    print("track points", len(case["trackPoints"]))
    print("ecfc nodes", len(ecfc["nodes"]), "edges", len(ecfc["edges"]))
    print("validation errors", ecfc["validation"]["errorCount"],
          "warnings", ecfc["validation"]["warningCount"])
    for i in issues:
        print(("ERR " if i["isError"] else "WARN"), i["ruleCode"], i["relatedNodeId"] or "", i["message"])
    print("quote checks:")
    for c in checks:
        print(("OK  " if c["matched"] else "FAIL"), c["id"], "p"+str(c["page"]), c["quote"][:40])


if __name__ == "__main__":
    main()
