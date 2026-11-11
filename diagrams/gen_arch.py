# 生成 MCIS-3D 整体系统架构图（SVG），再由 render.sh 用无头 Chrome 导出 PNG
W, H = 2400, 1600
FONT = "'Noto Sans CJK SC','Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif"
MONO = "'JetBrains Mono',Consolas,'Noto Sans Mono CJK SC',monospace"
K = {  # kind: (fill, stroke, title color)
 'base': ('#0d1a2e', '#2f6f86', '#e6f1ff'),
 'new':  ('#2a1f08', '#ffb020', '#ffe2a6'),
 'agent':('#1c1636', '#a78bfa', '#e9e3ff'),
 'store':('#0a2320', '#10b981', '#c9f7e6'),
 'src':  ('#111b29', '#6b84a6', '#dbe6f5'),
 'out':  ('#08202a', '#3be3ff', '#d7f8ff'),
}
out = []
def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def text(x, y, s, size=14, fill='#e6f1ff', anchor='start', weight=400, mono=False, op=1):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" font-family="{MONO if mono else FONT}" opacity="{op}">{esc(s)}</text>')
def rect(x, y, w, h, fill, stroke=None, rx=6, sw=1.4, dash=None, op=1):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"' + (f' stroke="{stroke}" stroke-width="{sw}"' if stroke else '') + (f' stroke-dasharray="{dash}"' if dash else '') + f' opacity="{op}"/>')
def line(pts, color='#8da4c4', w=2, dash=None, arrow_end=True, arrow_start=False):
    d = 'M' + ' L'.join(f'{x},{y}' for x, y in pts)
    m = (' marker-end="url(#ah-%s)"' % color.strip('#')) if arrow_end else ''
    m += (' marker-start="url(#as-%s)"' % color.strip('#')) if arrow_start else ''
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"' + (f' stroke-dasharray="{dash}"' if dash else '') + m + '/>')
def box(x, y, w, h, title, subs=(), kind='base', badge=None, star=False, tsize=14.5, ssize=12):
    f, s, tc = K[kind]
    rect(x, y, w, h, f, s, rx=6, sw=1.6 if kind == 'new' else 1.3)
    if kind == 'new': rect(x, y, 4, h, s, rx=2)
    cy = y + 22 if subs else y + h / 2 + 5
    text(x + w / 2, cy, title, tsize, tc, 'middle', 700)
    for i, sub in enumerate(subs):
        text(x + w / 2, cy + 18 + i * 16, sub, ssize, '#9fb3cf', 'middle')
    if badge:
        bw = 10 + 15 * len(badge)
        rect(x + w - bw - 4, y - 9, bw, 18, '#ffb020', None, rx=9)
        text(x + w - bw / 2 - 4, y + 5, badge, 12.5, '#1a1200', 'middle', 700)
    if star:
        text(x + 12, y + h - 9, '★', 14, '#ff3b5c', 'start', 700)

colors = ['#8da4c4', '#3be3ff', '#ffb020', '#a78bfa', '#10b981', '#ff3b5c']
defs = '<defs>' + ''.join(
    f'<marker id="ah-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
    f'<marker id="as-{c[1:]}" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10,0 L0,5 L10,10 z" fill="{c}"/></marker>' for c in colors) + \
    '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#07101d"/><stop offset="1" stop-color="#040910"/></linearGradient>' + \
    '<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0 L0 0 0 40" fill="none" stroke="rgba(59,227,255,0.05)" stroke-width="1"/></pattern></defs>'

rect(0, 0, W, H, 'url(#bg)', rx=0); rect(0, 0, W, H, 'url(#grid)', rx=0)
# 标题
text(40, 52, 'MCIS-3D 海事事故调查三维仿真系统 · 整体系统架构', 32, '#ffffff', weight=700)
text(40, 84, 'Unity 6 (URP) 客户端 × .mcase 案件包 × Python 智能体服务 · 含 P6+ 国际对标 14 项功能（①–⑭）落位 · 示例数据均为虚构（Lily × Mary）', 16, '#8da4c4')
rect(1868, 30, 492, 34, '#2a1f08', '#ffb020', rx=4)
text(2114, 53, '对标 IMO MSC.255(84) · A.1075(28) · COLREGs · MAIB/NTSB', 14, '#ffd166', 'middle', 600)

# ---------- 外部数据源 ----------
SX, SW = 30, 262
text(SX, 132, '外部数据源', 19, '#dbe6f5', weight=700); text(SX + 104, 132, 'INPUTS', 12, '#526987', mono=True)
srcs = [('AIS 记录', ['NMEA !AIVDM / CSV', 'VTS 岸基 · 船载'], None),
        ('VDR / S-VDR', ['驾驶台音频 · VHF · 雷达', '车钟 · 舵角 · 航向'], '①'),
        ('ECDIS 截屏 / 数据', ['航线 · 报警 · 截屏序列'], '①'),
        ('询问笔录', ['录音转写 · PDF · 手工录入'], '③'),
        ('调查报告 PDF', ['本案材料 · 历史报告库'], '⑫'),
        ('Cesium 倾斜摄影', ['3D Tiles · 地形 · 岸线'], None),
        ('气象水文 / 潮流', ['风 · 浪 · 能见度 · 流'], None)]
sy = 150; sh = 84; sg = 22
src_y = []
for i, (t, s, b) in enumerate(srcs):
    y = sy + i * (sh + sg)
    box(SX, y, SW, sh, t, s, 'src', badge=b)
    src_y.append(y + sh / 2)

# ---------- Unity 客户端 ----------
UX, UY, UW, UH = 330, 112, 1300, 1066
rect(UX, UY, UW, UH, 'rgba(59,227,255,0.035)', '#3be3ff', rx=10, sw=2)
rect(UX, UY, UW, 40, 'rgba(59,227,255,0.12)', None, rx=10)
text(UX + 18, UY + 27, 'Unity 6 客户端（Windows exe · URP · UI Toolkit + Painter2D）', 19, '#ffffff', weight=700)
text(UX + UW - 16, UY + 27, '命名空间 Mcis.*  ·  纯逻辑程序集用 dotnet + xUnit 测试', 13, '#8da4c4', 'end', mono=False)
layers = [
 ('UI 层', 'Mcis.UI', [('案件大厅 / 建案', ['向导 · 证据清单']), ('HUD · 时间轴', ['小地图 · CPA 告警']), ('船模 / 环境 / 航迹', ['编辑器']), ('ECFC 编辑器', ['论文 §2.5 / 表 4']), ('分析与复盘', ['D/DCPA/TCPA 曲线']), ('导出中心', ['PDF · MP4 · .mcase'])],
  [('证据中心', ['VDR 多轨回放'], '①②④', True), ('笔录比对', ['矛盾高亮'], '③', True), ('COLREG 对照', ['会遇时间带'], '⑥', True), ('What-if', ['参数滑块'], '⑦', False), ('人为因素', ['HFACS · 工休'], '⑤', False), ('系统分析', ['Bow-tie 等'], '⑧', False), ('建议与报告', ['看板 · 征求意见'], '⑨⑩⑪', True), ('知识库', ['相似 · 分级'], '⑫⑬', False), ('权限脱敏', ['角色矩阵'], '⑭', False)]),
 ('Presentation 层', 'Mcis.Presentation', [('CameraRig', ['驾驶台/跟随/俯视']), ('ShipView', ['EcfcCard3D 弹卡']), ('Cesium 适配', ['双精度原点平移']), ('OfflineRecorder', ['FFmpeg → MP4']), ('PdfReportExporter', ['MigraDoc · Noto SC']), ('Environment 视图', ['Enviro 3 / DWP2'])],
  [('VdrPlaybackView', ['音频波形 · 雷达 PPI 叠加'], '①', True), ('WhatIfCompareView', ['原/反事实双轨幽灵船'], '⑦', False), ('国际格式报告', ['IMO/MAIB · 中英双语', 'GISIS 字段导出'], '⑪', True), ('RedactedExporter', ['脱敏 · 水印 · 加密导出'], '⑭', False), ('ReviewPackBuilder', ['征求意见包 · 意见回收'], '⑩', True)]),
 ('Simulation 层', 'Mcis.Simulation', [('SimClock', ['TimelinePipeline']), ('ShipController', ['Nomoto · 姿态合成']), ('CpaService', ['DCPA/TCPA 1 Hz']), ('EnvironmentBridge', ['天气/水文时间线']), ('CollisionDamage', ['OBB 二分 tc · 进水']), ('EcfcService', ['卡片调度'])],
  [('VdrTrackSync', ['多轨统一时钟 · 跳转'], '①', True), ('ColregEngine', ['会遇局面判定', '应采取 vs 实际'], '⑥', True), ('CounterfactualRunner', ['情景分叉 · 重算 tc', '敏感性扫描'], '⑦', False), ('TestimonyLocator', ['陈述定位到时间轴'], '③', True)]),
 ('Domain 层', 'Mcis.Domain（纯 C#）', [('Ais 解码', ['NMEA · CSV']), ('Tracks 插值', ['Hermite · 剔除']), ('Geo 坐标', ['WGS84⇄ENU']), ('Cpa 计算', ['向量法']), ('Ecfc 模型', ['校验 · 布局']), ('Damage 模型', ['Q = Cd·A·√2gh'])],
  [('TimeAlignment', ['钟差 · 冲突检测'], '④', False), ('Testimony', ['陈述要素 · 比对'], '③', True), ('HumanFactors', ['HFACS · STCW'], '⑤', False), ('ColregRules', ['规则库 R5–R19'], '⑥', True), ('SystemicModels', ['Bow-tie/AcciMap'], '⑧', False), ('SafetyRec', ['建议 · 意见轮次'], '⑨⑩', True), ('Classification', ['分级 · 通知义务'], '⑬', False)]),
 ('Data 层', 'Mcis.Data', [('CaseRepository', ['.mcase 读写 · 校验']), ('AuditLog', ['CommandHistory']), ('AisImporter', ['NMEA / CSV']), ('SQLite 索引', ['P1 本地']), ('AgentClient', ['HTTP · 草稿回写']), ('Fixtures', ['Lily/Mary 虚构'])],
  [('VdrImporter', ['IEC 61996 包解析'], '①', True), ('CustodyLedger', ['保管链 · SHA-256'], '②', False), ('TestimonyImporter', ['转写 · PDF'], '③', True), ('AccessPolicy', ['RBAC · 字段级'], '⑭', False), ('KnowledgeRepo', ['pgvector 客户端'], '⑫', False)]),
]
LY0, LH = UY + 52, 200
MX0, MX1 = UX + 178, UX + UW - 14
layer_box = {}
for li, (nm, ns, row1, row2) in enumerate(layers):
    y = LY0 + li * (LH + 2)
    rect(UX + 10, y, UW - 20, LH - 6, 'rgba(13,26,46,0.55)' if li % 2 == 0 else 'rgba(20,36,60,0.45)', 'rgba(59,227,255,0.18)', rx=6, sw=1)
    text(UX + 24, y + LH / 2 - 8, nm, 16.5, '#3be3ff', weight=700)
    text(UX + 24, y + LH / 2 + 14, ns, 11.5, '#6b84a6', mono=True)
    for ri, row in enumerate((row1, row2)):
        n = len(row); gap = 10
        bw = (MX1 - MX0 - gap * (n - 1)) / n
        by = y + 14 + ri * 92; bh = 80
        for i, item in enumerate(row):
            bx = MX0 + i * (bw + gap)
            if ri == 0:
                box(bx, by, bw, bh, item[0], item[1], 'base', tsize=14 if bw > 140 else 13.5)
            else:
                box(bx, by, bw, bh, item[0], item[1], 'new', badge=item[2], star=item[3], tsize=14 if bw > 140 else 13.5, ssize=11.5 if bw < 130 else 12)
    layer_box[nm] = y

# 源 → Data 层（总线）
busx = 312
for yy in src_y[:5] + src_y[6:]:
    line([(SX + SW, yy), (busx, yy)], '#6b84a6', 1.6, arrow_end=False)
data_y = layer_box['Data 层']
line([(busx, src_y[0]), (busx, data_y + 60), (UX + 10, data_y + 60)], '#6b84a6', 2.2)
text(busx - 6, data_y + 82, '导入适配器', 12, '#8da4c4', 'end')
# Cesium → Presentation
pres_y = layer_box['Presentation 层']
line([(SX + SW, src_y[5]), (busx - 8, src_y[5]), (busx - 8, pres_y + 54), (UX + 10, pres_y + 54)], '#3be3ff', 1.8, dash='6 4')
text(SX + SW - 4, src_y[5] - 48, '', 12)

# ---------- Python 智能体服务 ----------
PX, PY, PW, PH = 1668, 112, 390, 1066
rect(PX, PY, PW, PH, 'rgba(167,139,250,0.05)', '#a78bfa', rx=10, sw=2)
rect(PX, PY, PW, 40, 'rgba(167,139,250,0.16)', None, rx=10)
text(PX + 16, PY + 27, 'Python 智能体服务（本机 sidecar）', 18, '#ffffff', weight=700)
box(PX + 16, PY + 56, PW - 32, 82, '编排层 Orchestrator', ['自研任务图（LangGraph 可选）', '分派 · 重试 · 预算 · 结果合并'], 'agent', tsize=15.5)
text(PX + 16, PY + 166, '6 个智能体', 14, '#c4b5fd', weight=700)
agents = [('船舶智能体', ['船舶参数 · 证书'], None), ('时间线智能体', ['事件 · 时钟对齐'], '①④'), ('环境智能体', ['气象 · 水文'], None), ('人员/作业智能体', ['笔录 · HFACS'], '③⑤'), ('原因→ECFC 智能体', ['规则 · 系统分析'], '⑥⑧'), ('汇总/校验智能体', ['一致性 · 报告稿'], '⑪')]
aw = (PW - 32 - 12) / 2
for i, (t, s, b) in enumerate(agents):
    ax = PX + 16 + (i % 2) * (aw + 12); ay = PY + 180 + (i // 2) * 88
    box(ax, ay, aw, 74, t, s, 'agent', badge=b, tsize=14)
ty = PY + 180 + 3 * 88 + 10
text(PX + 16, ty, '工具与护栏', 14, '#c4b5fd', weight=700)
tools = [('证据引用器', ['每条结论附 页码 + 原文']), ('RAG 检索', ['相似案例 ⑫ · 规则条文 ⑥']), ('脱敏网关 ⑭', ['PII 替换后才可出本机'])]
for i, (t, s) in enumerate(tools):
    box(PX + 16, ty + 14 + i * 70, PW - 32, 60, t, s, 'agent', tsize=14)
hy = ty + 14 + 3 * 70 + 6
box(PX + 16, hy, PW - 32, 66, '人工确认队列', ['智能体输出 = 草稿 → 调查员确认/驳回/修改'], 'new', tsize=15)
box(PX + 16, hy + 80, PW - 32, 60, '审计日志 audit/agent.jsonl', ['提示词 · 模型 · 引用 · 确认人 · 时间'], 'agent', tsize=14)
box(PX + 16, hy + 154, PW - 32, 62, '模型路由', ['本地 Qwen / DeepSeek（默认）', '国内 API（仅脱敏文本）'], 'agent', tsize=14)
box(PX + 16, hy + 230, PW - 32, 112, '本地 HTTP API（127.0.0.1）', ['/extract  /align  /colreg  /hf', '/rag  /draft  /validate', '只读 derived/ 脱敏副本 · 不触碰 raw/'], 'agent', tsize=14)

# Unity ↔ Python
dy = layer_box['Data 层'] + 54
line([(UX + UW, dy), (PX, dy)], '#a78bfa', 2.4, arrow_start=True)
text((UX + UW + PX) / 2, dy - 10, 'HTTP', 12, '#c4b5fd', 'middle', 700)
uy = layer_box['UI 层'] + 140
line([(PX, uy), (UX + UW, uy)], '#ffb020', 2, dash='5 4')
text((UX + UW + PX) / 2, uy - 10, '草稿', 12, '#ffd166', 'middle', 700)
rect(UX + UW - 2, dy + 14, 0.1, 0.1, 'none')

# ---------- 输出 ----------
OX, OW = 2090, 282
text(OX, 132, '输出', 19, '#d7f8ff', weight=700); text(OX + 46, 132, 'OUTPUTS', 12, '#526987', mono=True)
outs = [('PDF 调查报告', ['中文 / 中英双语', 'IMO · MAIB 模板'], '⑪'), ('MP4 仿真视频', ['多视角 · 原/反事实对比', '水印烧录'], '⑦'), ('GISIS 上报字段', ['JSON / CSV 校验导出'], '⑪'), ('安全建议跟踪表', ['对象 · 期限 · 落实状态'], '⑨'), ('征求意见包', ['30 天 · 加密 · 水印'], '⑩⑭'), ('.mcase 交付包', ['raw · derived · audit', 'SHA-256 清单'], '②'), ('分析图表 / ECFC 图', ['SVG · PNG'], None)]
oh, og = 94, 18
out_y = []
for i, (t, s, b) in enumerate(outs):
    y = 150 + i * (oh + og)
    box(OX, y, OW, oh, t, s, 'out', badge=b)
    out_y.append(y + oh / 2)
# 输出总线：Presentation → 顶部 → 输出列
bus_top = 100
px_ = UX + UW - 60
line([(px_, pres_y + 14), (px_, bus_top), (OX - 18, bus_top), (OX - 18, out_y[-1])], '#3be3ff', 2.2, arrow_end=False)
for yy in out_y:
    line([(OX - 18, yy), (OX, yy)], '#3be3ff', 2)
text((px_ + OX) / 2 + 160, bus_top - 8, 'Presentation 导出', 12.5, '#3be3ff', 'middle', 600)

# ---------- 存储 ----------
SY0 = 1214
rect(UX, SY0, PX + PW - UX, 156, 'rgba(16,185,129,0.05)', '#10b981', rx=10, sw=2)
text(UX + 18, SY0 + 28, '存储层', 18, '#c9f7e6', weight=700)
text(UX + 92, SY0 + 28, 'P1：.mcase + SQLite 单机 → 后续：PostgreSQL + PostGIS / MinIO / pgvector（多案件、团队协作）', 13.5, '#8da4c4')
stores = [('.mcase 案件包', ['raw/ 只读 · derived/ · evidence/', 'audit/*.jsonl · SHA-256 校验'], 'P1', '②'), ('SQLite', ['案件索引 · 缓存', '单机离线'], 'P1', None), ('PostgreSQL + PostGIS', ['多案件 · 轨迹空间查询', '建议/意见/权限表'], '后续', '⑨⑭'), ('MinIO 对象存储', ['VDR 音频 · 雷达帧', '视频 · 大文件'], '后续', '①'), ('pgvector', ['历史报告切片向量', '相似案例检索'], '后续', '⑫')]
n = len(stores); gap = 16; sx0 = UX + 18; sw_ = (PX + PW - UX - 36 - gap * (n - 1)) / n
for i, (t, s, ph, b) in enumerate(stores):
    x = sx0 + i * (sw_ + gap)
    box(x, SY0 + 46, sw_, 94, t, s, 'store', badge=b, tsize=15)
    rect(x + 8, SY0 + 52, 40, 18, '#10b981' if ph == 'P1' else 'rgba(16,185,129,0.25)', None, rx=3)
    text(x + 28, SY0 + 65, ph, 11.5, '#04140f' if ph == 'P1' else '#c9f7e6', 'middle', 700)
# Data → 存储；Python → 存储
line([(UX + 380, UY + UH), (UX + 380, SY0)], '#10b981', 2.2, arrow_start=True)
line([(UX + 900, UY + UH), (UX + 900, SY0)], '#10b981', 2.2, arrow_start=True)
line([(PX + 200, PY + PH), (PX + 200, SY0)], '#10b981', 2.2, arrow_start=True)

# ---------- 图例 / 优先级 ----------
LY = 1396
rect(30, LY, W - 60, 176, 'rgba(10,20,35,0.8)', 'rgba(59,227,255,0.22)', rx=8)
text(50, LY + 30, '图例', 16, '#ffffff', weight=700)
lg = [('base', 'P1–P5 已有 / 在做模块'), ('new', 'P6+ 新增模块（角标 = 功能编号）'), ('agent', 'LLM 智能体服务'), ('store', '存储'), ('src', '外部数据源'), ('out', '输出')]
for i, (k, t) in enumerate(lg):
    x = 50 + i * 196
    rect(x, LY + 44, 30, 18, K[k][0], K[k][1], rx=3, sw=1.6)
    text(x + 38, LY + 58, t, 13, '#c9d6e8')
text(1240, LY + 58, '★ = 第一批优先：① VDR 回放 · ③ 笔录比对 · ⑥ COLREG 对照 · ⑨ 安全建议管理', 14, '#ff8fa3', weight=700)
feats = ['① VDR 导入与多轨回放', '② 证据保管链', '③ 询问笔录与交叉比对', '④ 多源时间对齐/冲突', '⑤ 人为因素 HFACS/疲劳/BRM', '⑥ COLREG 逐条对照', '⑦ What-if 反事实仿真',
         '⑧ AcciMap/STAMP/Bow-tie', '⑨ 安全建议管理', '⑩ 报告草案征求意见', '⑪ 国际格式双语报告 + GISIS', '⑫ 相似案例检索', '⑬ 事故分级与通知义务', '⑭ 按角色/字段保密脱敏']
for i, f in enumerate(feats):
    x = 50 + (i % 7) * 330; y = LY + 100 + (i // 7) * 30
    text(x, y, f, 14, '#ffd166' if i in (0, 2, 5, 8) else '#c9d6e8', weight=600 if i in (0, 2, 5, 8) else 400)
text(W - 50, LY + 164, 'Mcis 架构图 v1 · 2026-11-11 · 所有演示数据虚构', 11.5, '#526987', 'end', mono=True)

svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + defs + ''.join(out) + '</svg>'
open(__file__.replace('gen_arch.py', 'mcis-architecture.svg'), 'w', encoding='utf-8').write(svg)
print('ok', len(svg))
