# -*- coding: utf-8 -*-
"""YANGZE 22 / VEGA DREAM：case.json 数据（全部来自公开调查报告原文与图）。"""
from datetime import datetime, timedelta, timezone
from _qsrc import src

BJ = timezone(timedelta(hours=8))
UTC = timezone.utc
Y, V = "yangze22", "vega_dream"


def bt(h, m, s=0, day=30, month=12, year=2024, approx=False):
    t = datetime(year, month, day, h, m, s, tzinfo=BJ)
    return {"beijing": t.isoformat(), "utc": t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "approximate": approx}


def geo_dm(lat_d, lat_m, lon_d, lon_m, original=None):
    return {"latDeg": round(lat_d + lat_m / 60.0, 6), "lonDeg": round(lon_d + lon_m / 60.0, 6),
            "latDm": f"{lat_d}°{lat_m}′N", "lonDm": f"{lon_d}°{lon_m}′E",
            "original": original or f"{lat_d}°{lat_m}′N {lon_d}°{lon_m}′E"}


LOC_REPORT = geo_dm(31, 16.9, 121, 49.7, "31°16.9′N 121°49.7′E")
LOC_Y_AIS_COL = geo_dm(31, 16.931, 121, 49.660, "31° 16.931′ 北 121° 49.660′ 东（图6 AIS信息框）")
LOC_V_AIS_COL = geo_dm(31, 16.884, 121, 49.859, "31° 16.884′ 北 121° 49.859′ 东（图6 AIS信息框）")


def vessels():
    y = {
        "vesselId": Y, "name": "YANGZE 22", "nameCn": None,
        "imoNumber": "9958212", "callSign": "9V9860", "mmsi": "563230200",
        "flagState": "新加坡", "portOfRegistry": "新加坡", "vesselType": "散货船", "vesselTypeCode": "BulkCarrier",
        "grossTonnage": 44479, "netTonnage": 27553, "loaM": 225.29, "beamM": 32.26, "moldedDepthM": 20.01,
        "mainEnginePowerKw": 9000, "summerDraftM": 14.467, "builtDate": "2022-11",
        "owner": "NEBULA SHIPPING PTE LTD.",
        "managerOperator": "Shanghai Run Yuan Shipping management Co, Ltd.（上海润元船舶管理有限公司）",
        "classSociety": "劳氏船级社",
        "lastAnnualSurvey": "2024-11-21 韩国光阳港，合格", "lastPsc": "2024-11-30 菲律宾伊利甘港，缺陷0项",
        "crewOnBoard": 21, "crewNationality": "中国", "pilotOnBoard": True,
        "bridgeTeamAtIncident": ["三副", "实习三副", "值班水手", "上海港引航员"],
        "voyage": {"from": "南通新世界通用码头", "to": "新加坡（加装燃油）后驶往巴西",
                   "departureBeijing": {"voyageSection": bt(9, 0, approx=True), "narrativeSection": bt(8, 30, approx=True),
                                        "conflict": "第11页航次情况写约0900时开航，第27页事故经过写约0830时开航；两处并存，未取舍"},
                   "maxDraftAtDepartureM": 11.98, "cargo": "化肥60250吨（散装粒状硫酸铵51195吨，散装过磷酸钙9055吨）", "holds": 7},
        "steeringGear": {"maker": "YDK Technologies（日本）", "model": "PT900-A-P", "manufactured": "2022-05",
                         "controlSystems": 2, "modes": ["AUTO", "FU", "NFU", "NFU OVERRIDE"],
                         "rudderAngleIndicators": 6, "helmScaleNote": "刻度盘随手轮转动，指针固定，指针所指刻度与操舵方向相反",
                         "conclusion": "事故前操舵系统工况正常",
                         "maxRudderDegFromTable": 35},
        "aisStaticInFigures": {"loaM": 229.0, "beamM": 32.0, "draftM": 11.9, "destination": "SGSIN",
                               "eta": "08-01-2024 02:00", "vesselTypeNr": 70,
                               "note": "AIS船长229 m与证书225.29 m不一致；ETA年份2024早于事发日期，疑为未更新的静态字段"},
        "fieldSources": {
            "imoNumber": src("IMO:9958212"),
            "callSign": src("船舶呼号：9V9860"),
            "mmsi": src("图6：碰撞时间和位置图", figure="图6", reading="YANGZE 22 AIS 信息框 MMSI: 563230200",
                        note="MMSI 仅见于图6、图28、图29 的 VTS AIS 信息框，正文未列"),
            "portOfRegistry": src("船籍港：新加坡"),
            "flagState": src("NEBULA SHIPPING PTE LTD.所属的新加坡籍散货船“YANGZE 22”轮"),
            "vesselType": src("船舶种类：散货船IMO:9958212"),
            "grossTonnage": src("总吨：44479"), "netTonnage": src("净吨：27553"),
            "loaM": src("船长：225.29米"), "beamM": src("型宽：32.26米"), "moldedDepthM": src("型深：20.01米"),
            "mainEnginePowerKw": src("主机功率9000kW"), "summerDraftM": src("夏季满载吃水：14.467米"),
            "builtDate": src("建造日期：2022年11月"), "owner": src("船舶所有人：NEBULA SHIPPING PTE LTD."),
            "managerOperator": src("该轮管理人、经营人均为Shanghai Run Yuan Shipping management Co, Ltd.。"),
            "lastAnnualSurvey": src("该轮最近一次年度检验由劳氏船级社于2024年11月21日在韩国光阳港实施，检验结果合格。"),
            "lastPsc": src("该轮最近一次PSC检查于2024年11月30日在菲律宾伊利甘港实施，发现缺陷0项。"),
            "crew": src("该轮船上共有船员21人，均为中国籍，其配员情况满足最低安全配员证书要求。事故发生前，三副、实习三副、值班水手及1名上海港引航员共4人在驾驶台。"),
            "voyageSection": src("2024年12月30日约0900时，“YANGZE 22”轮从南通新世界通用码头开航，开航时最大吃水约11.98米，计划先去新加坡加装燃油后驶往巴西。"),
            "cargo": src("该轮共有7个货舱，装载化肥60250吨，其中，装载散装粒状硫酸铵51195吨，散装过磷酸钙9055吨。"),
            "narrativeDeparture": src("2024年12月30日约0830时，该轮从南通新世界通用码头开航。"),
            "steeringGear": src("该轮使用的是日本YDK Technologies公司生产的PT900-A-P型操舵系统，生产日期为2022年5月，年度检验合格。"),
            "steeringModes": src("该操舵系统提供2套控制系统（No.1/No.2），可选择其中一套操舵系统使用自动舵（AUTO）、随动操舵（FU）或非随动操舵（NFU）。此外，该轮操舵系统还配备了越控操舵（NFU OVERRIDE）操舵模式"),
            "helmScale": src("操舵时，刻度盘随手轮转动，指针固定不动，指针指示的刻度与操舵方向相反。"),
            "rudderIndicators": src("该轮共配有6个舵角指示器，均独立于操舵系统"),
            "steeringConclusion": src("经综合分析，认定事故发生前“YANGZE 22”轮操舵系统工况正常。"),
            "aisStatic": src("图6：碰撞时间和位置图", figure="图6",
                             reading="船长229.0米，船宽32.0米，吃水11.9米，目的地SGSIN，ETA 08-01-2024 02:00"),
        },
    }
    v = {
        "vesselId": V, "name": "VEGA DREAM", "nameCn": None,
        "imoNumber": "9532094", "callSign": "7KNE", "mmsi": "431860000",
        "flagState": "日本", "portOfRegistry": "东京", "vesselType": "散货船", "vesselTypeCode": "BulkCarrier",
        "grossTonnage": 91468, "netTonnage": 57660, "loaM": 283.3, "beamM": 45.0, "moldedDepthM": 24.7,
        "mainEnginePowerKw": 16860, "summerDraftM": 18.03, "builtDate": "2010-04",
        "owner": "Mitsui O.S.K. Lines, Ltd.", "managerOperator": "MASGSAYSAY MOL SHIP MANAGEMENT INC.（报告原文拼写）",
        "classSociety": "日本船级社",
        "lastAnnualSurvey": "2024-03-26 土耳其伊斯肯德伦湾，合格", "lastPsc": "2023-12-13 澳大利亚丹皮尔港，缺陷0项",
        "crewOnBoard": 20, "crewNationality": "菲律宾", "pilotOnBoard": True,
        "bridgeTeamAtIncident": ["船长", "三副", "值班水手", "上海港引航员"],
        "voyage": {"from": "湛江", "to": "张家港", "departureBeijing": bt(22, 15, day=24, approx=True),
                   "maxDraftAtDepartureM": 11.98, "cargo": "铁矿97035吨", "holds": 9,
                   "note": "两船开航最大吃水在报告中均写约11.98米；图6/图28 AIS吃水为12.0米"},
        "aisStaticInFigures": {"loaM": 290.0, "beamM": 45.0, "draftM": 12.0, "destination": "CNZJG",
                               "eta": "30-12-2024 18:43", "vesselTypeNr": 70,
                               "note": "AIS船长290 m与证书283.3 m不一致"},
        "fieldSources": {
            "imoNumber": src("IMO:9532094"), "callSign": src("船舶呼号：7KNE"), "portOfRegistry": src("船籍港：东京"),
            "flagState": src("Lines,Ltd.所属的日本籍散货船“VEGA DREAM”轮"),
            "mmsi": src("图6：碰撞时间和位置图", figure="图6", reading="VEGA DREAM AIS 信息框 MMSI: 431860000",
                        note="MMSI 仅见于 VTS AIS 信息框（图6、图28、图29），正文未列"),
            "grossTonnage": src("总吨：91468"), "netTonnage": src("净吨：57660"),
            "loaM": src("船长：283.3米"), "beamM": src("型宽：45米"), "moldedDepthM": src("型深：24.7米"),
            "mainEnginePowerKw": src("主机功率16860kW"), "summerDraftM": src("夏季满载吃水：18.03米"),
            "builtDate": src("建造日期：2010年4月"), "owner": src("船舶所有人：Mitsui O.S.K. Lines, Ltd."),
            "managerOperator": src("船舶经营人/管理人：MASGSAYSAY MOL SHIP MANAGEMENT INC."),
            "lastAnnualSurvey": src("该轮最近一次年度检验由日本船级社于2024年3月26日在土耳其伊斯肯德伦湾实施，检验结果合格。"),
            "lastPsc": src("该轮最近一次PSC检查于2023年12月13日在澳大利亚丹皮尔港实施，发现缺陷0项。"),
            "crew": src("该轮船上共有船员20人，均为菲律宾籍"),
            "bridgeTeam": src("事故发生前，船长、三副、值班水手及1名上海港引航员共4人在驾驶台。"),
            "voyage": src("2024年12月24日约2215时，“VEGA DREAM”轮从湛江开航，开航时最大吃水约11.98米，计划驶往张家港。"),
            "cargo": src("轮共9有个货舱，装载铁矿97035吨。", note="原文“共9有个货舱”为笔误，按9个货舱记录"),
            "aisStatic": src("图28：2200时38秒吴淞VTS监控", figure="图28",
                             reading="船长290.0米，船宽45.0米，吃水12.0米，目的地CNZJG，ETA 30-12-2024 18:43"),
        },
    }
    return [y, v]


def personnel():
    P = {Y: [], V: []}
    def add(vid, **k):
        P[vid].append(k)
    add(Y, role="船长", name="邹**", nationality="中国", born="1972-07-24",
        certificate="无限航区3000总吨及以上船舶船长（山东海事局 2024-11-01 签发，有效至2029-11-01）",
        experience="2011-06-29 首次取得船长证书，2012-12 初任船长，已任16艘船船长", joined="2024-12-27 南通",
        atIncident="事故前约10分钟离开驾驶台，碰撞发生时回到驾驶台",
        source=src("邹**于2024年12月27日在南通上“YANGZE 22”轮任职船长。事故发生前约10分钟离开驾驶台，在碰撞发生时回到驾驶台。"))
    add(Y, role="三副（值班驾驶员）", name="辛**", nationality="中国", born="1991-07-18",
        certificate="无限航区500总吨及以上船舶三副（天津海事局 2024-02-01 签发，有效至2029-02-01）",
        experience="2015-06 初任三副，已任10艘船三副", joined="2024-12-27 南通",
        atIncident="驾驶台值班，负责操纵车钟和协助瞭望；约1945时接班",
        source=src("2024年12月27日，辛**在南通上“YANGZE 22”轮任职三副。事故发生时其在驾驶台值班，负责操纵车钟和协助瞭望。"))
    add(Y, role="值班水手（操舵）", name="丁**", nationality="中国", born="1988-11-23",
        certificate="500总吨及以上船舶高级值班水手（天津海事局，有效至2053-11-23）",
        experience="2022-03 见习水手，2023-01 正式任值班水手；此前3艘船：HEIDI A 57天、ANSHUN II 66天、汇通78 353天",
        joined="2024-11-22 韩国",
        regularSchedule={"type": "白班水手", "atSea": ["0800-1200", "1300-1700"], "inPort": ["0400-0800", "1600-2000"],
                         "bridgeWatchExperienceOnThisShip": "未在驾驶台值过班"},
        atIncident="驾驶台操舵；当日约0914时接替李**操舵，约1936时到驾驶台接班操舵",
        source=src("上船后被安排为白班水手，白天工作晚上休息（海上工作时间0800-1200/1300-1700，港内工作时间0400-0800/1600-2000），未在驾驶台值过班。"),
        sourceExperience=src("丁**于2022年3月首次上船任职见习水手，2023年1月正式任职值班水手，之前共在3艘船舶上任职"),
        sourceDuty=src("事故当日，丁**根据大副安排上驾驶台接替水手李**。事故发生时其在驾驶台操舵。"))
    add(Y, role="实习三副", name="刘**", nationality="中国", born="1981-04-15",
        certificate="500总吨及以上船舶值班水手（青岛海事局 2021-06-25 签发，有效至2046-04-15）",
        joined="2024-05-31 越南", atIncident="事故前在驾驶台跟班学习，碰撞前离开驾驶台去船长房间通知船长后未再上驾驶台",
        source=src("事故发生前其在驾驶台跟班学习，碰撞前离开驾驶台去船长房间通知船长后未再上驾驶台。"))
    add(Y, role="上海港引航员", name="周**", nationality="中国", born="1973-12-08",
        certificate="一级海港引航员（上海海事局 2024-05-13 签发，有效至2029-05-13），引领范围上海港及附近水域",
        boarded=bt(20, 1, approx=True), boardedAt="宝山航道68号浮至70号浮之间水域",
        atIncident="为YANGZE 22提供引航服务",
        source=src("周**于2024年12月30日约2001时在宝山航道68号浮至70号浮之间水域登上“YANGZE 22”轮。"))
    add(Y, role="原操舵水手（当日上午被替换）", name="李**", nationality=None, born=None, certificate=None,
        atIncident="约0914时被船长发现操反舵，由丁**接替",
        source=src("船长邹**发现操舵水手李**出现操反舵的情况，遂通知大副更换操舵水手。"))
    add(V, role="船长", name="HERMAN MURODA****", nationality="菲律宾", born="1973-10-01",
        certificate="无限航区船长（菲律宾主管当局，有效至2029-01-24）", joined="2024-03-22 土耳其",
        atIncident="驾驶台监航",
        source=src("HERMAN MURODA****于2024年3月22日在土耳其上“VEGA DREAM”轮任职船长。事故发生时其在驾驶台监航。"))
    add(V, role="三副（值班驾驶员）", name="JULIUS ALLAN ****", nationality="菲律宾", born="1993-03-16",
        certificate="无限航区三副（菲律宾主管当局，有效至2026-07-18）", joined="2024-06-08 中国烟台",
        atIncident="驾驶台值班，负责协助瞭望和操纵车钟",
        source=src("事故发生时其在驾驶台值班，负责协助瞭望和操纵车钟。"))
    add(V, role="值班水手（操舵）", name="ROBERT JAY ****", nationality="菲律宾", born="1989-02-24",
        certificate="无限航区水手（菲律宾主管当局，长期有效）", joined="2024-03-22 土耳其", atIncident="驾驶台操舵",
        source=src("于2024年3月22日在土耳其上“VEGA DREAM”轮任职水手。事故发生时其在驾驶台操舵。"))
    add(V, role="上海港引航员", name="杜**", nationality="中国", born="1981-10-23",
        certificate="一级海港引航员（上海海事局 2022-09-14 签发，有效至2027-09-14）",
        boarded=bt(18, 30, approx=True), boardedAt="长江口深水航道5号灯浮北侧", atIncident="为VEGA DREAM提供引航服务",
        source=src("杜**于2024年12月30日约1830时在长江口深水航道5号灯浮北侧登轮。"))
    return {
        Y: P[Y], V: P[V],
        "note": "姓名保持报告原有脱敏写法；报告中的部分身份证号与证书编号已脱敏，本文件不收录身份证号。"
                "报告未提供任何船员的实际工作/休息时间记录（仅有丁**的白班作息安排），无法做 STCW A-VIII/1 工休合规计算。",
    }


def environment():
    return {
        "narrativeAtIncident": {
            "weather": "晴", "visibilityText": "5海里以上", "visibilityNmMin": 5,
            "windFrom": "偏北风", "windFromDirDeg": None, "windBeaufort": "2~3",
            "windSpeedMps": None, "currentToDir": "西北流", "currentToDirDeg": None, "currentSpeedKn": 1.5,
            "tidePhase": "涨水", "lunarDate": "农历十一月三十", "waveHeightM": None,
            "source": src("天气：晴能见距离：5海里以上风向：偏北风风力：2~3级流向：西北流流速：约1.5节"),
            "tideSource": src("事故发生当天为农历十一月三十，当日横沙水文站潮汐情况：1850时/潮高86cm，2336时/潮高297cm。事故发生时间约为2202时，正值涨水。"),
            "notes": ["风向只有“偏北”、流向只有“西北”，未给度数；浪高未给。",
                      "能见度良好（>5 nm）且为夜间（约22时）；两船互见，适用COLREG第二章第一、二节（R4–R18），不属于R19能见度不良。"],
        },
        "tideStation": {"name": "横沙水文站", "date": "2024-12-30",
                        "extrema": [{"time": bt(18, 50), "heightCm": 86}, {"time": bt(23, 36), "heightCm": 297}],
                        "datum": None, "datumNote": "报告未写潮高基准面"},
        "waterway": {
            "name": "长江口深水航道", "location": "39号灯浮下游水域，横沙东锚地南侧、横沙通道交汇口附近",
            "bottomWidthM": 350, "sideSlopeWidthM": 100, "maintainedDepthM": 12.5,
            "trafficSeparation": "航道分隔线分隔出口（下行）与进口（上行）通航分道",
            "trafficControl": {"rule": "长兴高潮前4小时至前1小时为交通管制时段，进入深水航道须编队航行",
                               "changxingHighWater": bt(0, 16, day=31), "controlWindow": [bt(20, 16), bt(23, 16)],
                               "atIncident": "处于管制时段，进出深水航道船舶密度较大"},
            "channelBearingDeg": None,
            "channelBearingNote": "报告未给航道走向；两船正常航行航向分别约113–114°（出口）与294–295°（进口）",
            "buoyCoordinates": None,
            "buoyNote": "报告引用了41、39、38、37、35、31、25号灯浮和圆圆沙灯船，但未给出其坐标",
            "source": src("该水域的长江口深水航道底宽约350米，两侧有宽约100米的边坡水域，维护水深为12.5米。"),
            "controlSource": src("31日长兴高潮为0016时，长江口深水航道管制时段为30日2016时至2316时，本起事故发生时正处于长江口深水航道交通管制时段，进出深水航道船舶密度较大。"),
            "locationSource": src("事故发生在长江口深水航道39号灯浮下游水域，位于横沙东锚地南侧、横沙通道交汇口附近"),
        },
    }


def damage_and_collision():
    return {
        "collision": {
            "time": bt(22, 1, 54),
            "timeBasis": "吴淞VTS回放两船雷达回波及AIS信号接触时刻，且两船VDR同时可听到碰撞声响，结合人员陈述",
            "timeSource": src("回放吴淞VTS监控，两船雷达回波及AIS信号发生接触的时间为2024年12月30日2201时54秒，且此时两船的VDR中可以听到船舶碰撞时发出的声响"),
            "summaryTimeNote": "报告简况写“约2202时”，第14–15页认定2201时54秒；以后者为准，简况为约数",
            "summaryTimeSource": src("2024年12月30日约2202时，"),
            "location": LOC_REPORT,
            "locationBasis": "以碰撞时刻YANGZE 22 AIS船位为碰撞位置",
            "locationSource": src("以事故发生时“YANG ZE 22”轮的AIS船位为碰撞位置，即长江口深水航道39号灯浮下游进口航道内，概位：31°16.9′N121°49.7′E。"),
            "yangze22AisInFigure": {**LOC_Y_AIS_COL, "cogDeg": 54, "sogKn": 7.9, "hdgDeg": 47.0, "rotDegPerMin": 3},
            "vegaDreamAisInFigure": {**LOC_V_AIS_COL, "cogDeg": 295, "sogKn": 10.2, "hdgDeg": 297.0, "rotDegPerMin": 0},
            "aisFigureSource": src("图6：碰撞时间和位置图", figure="图6",
                                   reading="VTS 时钟 22:01:54 30-12-2024；YANGZE 22 航向54° 航速7.9kn 船首向47.0 转向速率3°/min Pos 31°16.931′N 121°49.660′E；"
                                           "VEGA DREAM 航向295° 航速10.2kn 船首向297.0 转向速率0°/min Pos 31°16.884′N 121°49.859′E"),
            "yangze22HeadingDeg": 47, "vegaDreamHeadingDeg": 297, "collisionAngleDeg": 70,
            "angleSource": src("碰撞发生时，“VEGA DREAM”轮艏向约为297°，“YANG ZE 22”轮艏向约为047°，计算可得两船碰撞角度约为70°（取锐角）"),
            "yangze22SpeedKn": 8.0, "vegaDreamSpeedKn": 10.2,
            "speedSources": [src("2201时54秒，该轮航向约047°，航速约8.0节。"), src("2201分54秒，该轮航向约297°，航速约10.2节。", note="原文“2201分54秒”为笔误，应为2201时54秒")],
            "contact": "VEGA DREAM 船首（正中部/球鼻艏）撞入 YANGZE 22 右舷中部第5号货舱位置",
            "contactSource": src("“VEGA DREAM”轮船首与“YANG ZE 22”轮右舷中部第5号货舱位置船体发生碰撞。"),
        },
        "hullDamage": {
            Y: {"frames": "Fr102–Fr131", "breachForeEndFromBowM": 115, "breachWidthM": 12, "breachHeightM": 16,
                "shape": "椭圆形（中间略窄）", "compartments": ["第5号货舱", "1号右燃油舱"],
                "source": src("该轮右舷肋位Fr102至Fr131之间的船壳破损，破口前端距船首约115米，破口宽度约12米（12～20米位置凹陷变形），破口高度约16米（离主甲板4米处严重变形）；"),
                "compartmentSource": src("破洞形状：椭圆形（中间略窄）。第5号货舱和1号右燃油舱破损。")},
            V: {"holes": [
                {"id": 1, "position": "球鼻艏前部偏左，水下约2米", "widthM": 1.0, "heightM": 0.3},
                {"id": 2, "position": "球鼻艏前部破洞1下方偏左，水下约4米", "widthM": 1.5, "heightM": 0.5},
                {"id": 3, "position": "球鼻艏根部连接船体，水下约1米起延续至底部，窄三角形", "widthM": 2.5, "heightM": 12},
                {"id": 4, "position": "艏尖舱右前重载水线以上（水上）", "widthM": "0.5～1", "heightM": 6}],
                "compartments": ["艏尖舱"],
                "source": src("该轮艏尖舱和球鼻艏水线以下有三处破洞，艏尖舱水线以上有一处破洞。"),
                "holeSources": [src("破洞1：水下2米左右，在球鼻艏前部偏左位置。破洞宽度约1米，高度约0.3米。"),
                                src("破洞2：水下4米左右，在球鼻艏前部破洞1下方偏左位置。宽度约1.5米，高度约0.5米。"),
                                src("破洞3：水下1米左右开始，在球鼻艏根部连接船体位置，一直延续至底部，呈窄三角形。底部最大宽度约2.5米，高度约12米。"),
                                src("破洞4：水上破洞，在艏尖舱右前重载水线以上，宽度约0.5～1米不等，高度约6米。")]},
        },
    }


def consequences():
    return {
        "grade": "较大等级水上交通事故", "casualties": "无人员伤亡",
        "gradeSource": src("事故未造成人员伤亡，构成较大等级水上交通事故。"),
        Y: {"hull": "右舷船中第5货舱部位破损，破口约12×16米，附近严重凹陷变形",
            "cargoLoss": "舱内约8750吨散装粒状硫酸铵全部损失", "oilSpilledT": 171.053,
            "source": src("舱内共计约8750吨散装粒状硫酸铵全部损失；1号右油舱内共计约171.053吨燃油泄漏入江。")},
        V: {"hull": "球鼻艏及上方船体破损；艏尖舱水线以上1处、水线以下3处破口，艏尖舱进水",
            "source": src("该轮球鼻艏及球鼻艏上方船体有破损，其中艏尖舱水线以上有1处破口，水线以下3处破口，艏尖舱内进水。")},
        "economicLoss": None, "economicLossNote": "报告未给出直接经济损失金额",
        "oilSpill": {
            "fuel": "LSFO 380", "bunkered": {"date": "2024-12-17", "place": "日本", "totalT": 359.990, "toNo1StbdT": 264.798},
            "no1StbdBeforeT": 267.197, "transferredToVegaForepeakT": 83.4, "recoveredFromTankT": 8.5, "pumpedOutT": 4.244,
            "spilledT": 171.053, "formula": "267.197-83.4-8.5-4.244=171.053",
            "source": src("该轮于2024年12月17日在日本加装燃油（油品：LSFO380）共计约359.990吨，其中该轮1号右燃油舱（泄漏舱）内共加注燃油约264.798吨，加注燃油后1号右燃油舱实际共存有燃油约267.197吨。"),
            "formulaSource": src("267.197-83.4-8.5-4.244=171.053吨。"),
            "surface": "横沙通道603灯浮、深水航道37–35灯浮、31–25灯浮间零星油污带；至2025-01-02水面油污清除完毕",
            "surfaceSource": src("油污主要分布在横沙通道603灯浮、长江口深水航道37灯浮至35灯浮之间、31灯浮至25灯浮之间等区域。"),
            "shore": "横沙岛西岸约1.5海里岸滩（芦苇地），新民港至红星港，面积约9000平方米，收割回收芦苇及油污混合物约116.2吨",
            "shoreSource": src("油污对事故发生地附近横沙通道东侧（横沙岛西岸）长约1.5海里岸滩（芦苇地）造成了污染，油污主要集中在新民港至红星港之间的沿岸芦苇地，面积约9000平方米，通过收割回收了芦苇及油污混合物约116.2吨。"),
            "sensitive": "未对饮用水源、湿地、自然保护区造成损害",
            "sensitiveSource": src("未对长江口水域周边饮用水源及湿地、自然保护区等敏感区域造成损害。"),
            "recoveredOilyWaterT": 811,
            "recoveredSource": src("2025年1月2日约1720时，事故现场共已回收含油污水约811吨"),
        },
    }


def causes_liability():
    return {
        "directCauses": [
            {"id": "DC1", "vesselId": Y, "text": "操舵水手错误执行引航员指令（把定航向时向左压舵；右满舵令下操左舵至左满舵；左满舵令下操右舵至右满舵）",
             "violates": "《中华人民共和国船员条例》第十六条第三款",
             "source": src("“YANGZE 22”轮操舵水手错误执行引航员指令。事故发生前，“YANGZE 22”轮沿长江口深水航道下行通航分道航行。操舵水手在执行引航员把定航向的指令时，发现船首有向左偏转趋势，错误采取向左压舵措施；"),
             "violatesSource": src("该行为违反了《中华人民共和国船员条例》第十六条第三款1的规定。")},
            {"id": "DC2", "vesselId": Y, "text": "值班三副未对操舵水手舵令执行情况进行有效检查并及时纠正（未监舵）",
             "violates": "STCW 规则 第A-VIII/2节第34条第1款",
             "source": src("操舵水手错误地执行了引航员指令，反向操舵，但值班三副未对操舵水手舵令执行情况进行有效检查，并及时纠正。"),
             "violatesSource": src("该行为违反了《1978年海员培训、发证和值班标准国际公约》第A-Ⅷ/2节第34条第1款2的规定。")},
            {"id": "DC3", "vesselId": Y, "text": "紧急情况下采取措施不当：误判为舵效差，未使用非随动/越控操舵，也未停车、倒车",
             "violates": "COLREG 1972 第8条第5款（报告写“第八条第五款”，对应现行条文 Rule 8(e)）",
             "source": src("但未采取非随动操舵或越控操舵操纵本船，也未采取停车、倒车等应急措施。"),
             "violatesSource": src("该行为违反了《1972年国际海上避碰规则》第八条第五款3的规定。")},
            {"id": "DC4", "vesselId": V, "text": "紧迫危险形成后未采取应急抛锚等有效措施",
             "violates": None, "violatesNote": "报告未列具体条款",
             "source": src("“YANGZE 22”轮船首越过航道分隔线侵入进口航道时，两船已经构成紧迫危险局面，“VEGA DREAM”轮未采取应急抛锚等有效措施。")},
        ],
        "indirectCauses": [
            {"id": "IC1", "vesselId": Y, "text": "船长临时离开驾驶台，未指定三副代职，也未告知引航员",
             "violates": "《船舶引航管理规定》第三十三条第四款；《长江口深水航道通航安全管理办法》第六条",
             "source": src("事故发生前，“YANGZE 22”轮船长临时离开驾驶台，未告知当时在驾驶台值班的三副代履行其职责，也未告知引航员")},
            {"id": "IC2", "vesselId": None, "text": "两船未建立有效联系（YANGZE 22 在 CH06 多次呼叫对方引航员姓名）",
             "source": src("“YANGZE 22”轮通过VHF CH06频道多次呼叫“VEGA DREAM”轮引航员姓名，“VEGA DREAM”轮虽然在VHF CH06频道收到上述呼叫，但两船未建立有效通信联系。")},
            {"id": "IC3", "vesselId": None, "text": "航道内避让时间和空间有限：底宽约350米，船首距离不到0.5海里，相对速度约19.8节，会遇时间不到2分钟",
             "source": src("与进口船“VEGA DREAM”轮之间的船首距离不到0.5海里，两船相对速度约19.8节、会遇时间不到2分钟，给事故双方船舶采取避免碰撞行动的时间和空间有限。")},
        ],
        "liability": {
            "collision": {Y: "主要责任", V: "次要责任"},
            "pollution": "两船均对污染事故负有责任（违反《海洋环境保护法》第八十一条）",
            "source": src("“YANGZE 22”轮承担本起碰撞事故主要责任，“VEGA DREAM”轮承担次要责任。"),
            "pollutionSource": src("两船均对该起污染事故负有责任。"),
        },
        "findings": [
            {"id": "F1", "text": "管理公司未对操舵系统（尤其越控操舵模式）进行针对性培训和指导，驾驶台人员不熟悉该模式操作和应用场景",
             "source": src("管理公司未对该轮操舵系统进行针对性培训和指导，尤其是越控操舵模式的指导，致使驾驶台人员对该模式操作和应用场景均不熟悉。")},
            {"id": "F2", "text": "当日上午发现原操舵水手操反舵后仅更换水手，未对接替水手进行针对性操舵培训",
             "source": src("没有引起重视，虽然采取了更换操舵水手的措施，但未对接替的操舵水手进行针对操舵培训。")},
            {"id": "F3", "text": "引航员之间在CH06直呼姓名而不呼船名呼号，对方船其他值班人员（尤其外籍船员）无法接收；对方引航员忙于操纵时不能有效守听",
             "source": src("虽然引航员之间呼叫对方姓名能被对方引航员直接清晰地接收，但无法被对方船舶的其他驾驶值班人员接收，尤其是外籍船员；")},
        ],
        "enforcementRecommendations": [
            {"target": "YANGZE 22 操舵水手丁**", "role": "直接责任人", "basis": "《海上交通安全法》第九十九条", "action": "建议吴淞海事局行政处罚",
             "source": src("“YANGZE 22”轮操舵水手丁**错误执行引航员指令、反向操舵，是本起事故的直接责任人")},
            {"target": "YANGZE 22 三副辛**", "role": "间接责任人", "basis": "《海上交通安全法》第九十九条", "action": "建议行政处罚（可从轻或减轻）",
             "source": src("“YANGZE 22”轮三副辛**未进行有效监舵，紧急情况下采取措施不当，是本起事故的间接责任人")},
            {"target": "YANGZE 22 引航员周**", "role": None, "basis": "《引航员管理办法》第四十四条", "action": "建议行政处罚（可从轻或减轻）",
             "source": src("“YANGZE 22”轮引航员周**未能结合当时的情况进行充分评估，错误判断为舵效差，未下达应急操舵指令")},
            {"target": "YANGZE 22 船长", "role": "管理责任", "basis": "《海上交通安全法》第九十九条", "action": "建议行政处罚（可从轻或减轻）",
             "source": src("“YANGZE 22”轮船长未在驾驶台值班，临时离开驾驶台未指定代职驾驶员，也未告知引航员")},
            {"target": "VEGA DREAM 船长、引航员杜**", "role": "次要责任方", "basis": None, "action": "建议免予处罚",
             "source": src("建议吴淞海事局对船长HERMAN MURODA****、引航员杜**免予处罚。")},
            {"target": "两船（污染）", "role": None, "basis": "《海洋环境保护法》第一百一十五条", "action": "建议行政处罚",
             "source": src("的规定，建议吴淞海事局对两船实施行政处罚。")},
            {"target": "两船船旗国政府", "role": None, "basis": None, "action": "通报事故情况",
             "source": src("建议将本起碰撞事故情况通报两船船旗国政府。")},
        ],
        "safetyRecommendations": [
            {"id": "SR-YZ-01", "addressee": "上海润元船舶管理有限公司", "title": "加强驾驶台资源管理",
             "text": "引航员操纵期间确保信息交流共享；船长和驾驶员切实履行监舵职责，核实引航员指令与实际执行；狭水道等特殊航段船长在驾驶台值班，暂离须告知值班驾驶员代职并告知引航员",
             "linkedCauses": ["DC2", "IC1"],
             "source": src("加强驾驶台资源管理。督促船舶严格落实驾驶台航行值班相关规定，特别是引航员操纵期间，要确保航行安全信息的交流和共享，船长和驾驶员要切实履行监舵职责")},
            {"id": "SR-YZ-02", "addressee": "上海润元船舶管理有限公司", "title": "加强船员操作培训和应急演练",
             "text": "强化刻度盘随手轮转动、指针所指刻度与操舵方向相反的操作培训；熟悉不同型号舵机操舵模式；将操舵模式转换纳入舵机失控演练；操作手册常规测试涵盖越控操舵",
             "linkedCauses": ["DC1", "DC3", "F1", "F2"],
             "source": src("加强船员操作培训和应急演练。强化对操舵时刻度盘随手轮转动，指针固定不动，指针指示的刻度与操舵方向相反情况的操作培训；")},
            {"id": "SR-YZ-03", "addressee": "上海港引航站", "title": "提升引航员应变反应能力",
             "text": "充分评估验证航行安全信息；了解船上紧急操舵模式和安装位置；密切关注指令是否被正确执行并及时纠正",
             "linkedCauses": ["DC3"],
             "source": src("提升引航员应变反应能力。要督促引航员对航行安全信息进行充分的评估和验证，确保操纵和避碰决策及时、正确；")},
            {"id": "SR-YZ-04", "addressee": "上海港引航站", "title": "优化和规范引航员之间的通信",
             "text": "针对引航员间直呼姓名、未呼船名呼号的问题开展分析研究，优化和规范通信方式",
             "linkedCauses": ["IC2", "F3"],
             "source": src("建议对上海港引航员之间通信方式开展分析研究，优化和规范引航员之间的通信。")},
        ],
    }
