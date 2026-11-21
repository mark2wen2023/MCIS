"""Opt-in adapter shell using existing workbench HTML/CSS. No data or transport.
The default build.py, demo JS and all previous hashes remain untouched.
"""
import argparse
from pathlib import Path

HERE=Path(__file__).resolve().parent


def build(output, *, display_only=False):
    html=(HERE/'workbench.html').read_text()
    script=(HERE/'registered.js').read_text()
    if display_only:
        marker='const DISPLAY_ONLY = false;'
        if script.count(marker)!=1:raise ValueError('Display boundary changed')
        script=script.replace(marker,'const DISPLAY_ONLY = true;')
    changes={
        '案件 / 合成双船会遇':'案件 / 登记原件查询',
        '<span class="badge">合成案件</span>':'<span class="badge">内部查询</span>',
        '<strong>双船会遇复盘</strong><code>SYN-XREPO-001</code>':'<strong>当前查询案件</strong><code id="registered-case">未选案件</code>',
        '<p><i class="dot a"></i>设备记录 <span>1 条已对齐</span></p><p><i class="dot amber"></i>未核实记录 <span class="amber-text">1 条独列</span></p>':'<p>独立设备记录未接入此查询</p>',
        '合成离线候选 · 非运行验收':'登记查询适配候选 · 业务未接线',
        '同一时点合成位置及历史输入示意，键盘可用下方记录按钮':'当前精确点示意，键盘可用下方记录按钮',
        '合成坐标网格 · 非海图 / 非等距':'当前点自适应示意 · 非海图 / 非等距',
        '细线为历史输入连接，不是当前船位；不越过缺口。已有插值用虚线，缺艏向不绘制确定船体。':'仅显示本次精确点；不绘历史连接。已存插值另标，缺艏向不绘制确定船体。',
        '<div class="step-controls">':'<div class="step-controls"><button id="registered-load" disabled>查询当前时点</button>',
        'A船B船与已对齐设备三轨时间轴；请选择上方时点':'两份原件当前查询状态；查询时点不是连续轨迹',
        '只在已有时点定位':'选点与前后移动仅暂选；点击查询才读取并登记访问。查询时间列表不是观测证明',
        '查看原始 JSON 与定位　›':'原文未接入 · 须另经授权读取',
        '完整原始记录':'原文不在此模型中',
        '<section class="other">':'<section class="other" hidden>',
        '离线交互候选 / 仅合成数据 · 非实际三维验收':'内部查询适配候选 / 无默认身份、查询或业务接线',
        '<dt>来源 UTC</dt>':'<dt>原件记载 UTC</dt>',
        '<dt>对齐 UTC</dt>':'<dt>展示对齐 UTC</dt>',
        'PAYLOAD':'{}',
        '/* STYLE */':(HERE/'style.css').read_text(),
        '/* SCRIPT */':script,
    }
    for before,after in changes.items():
        if html.count(before)!=1:raise ValueError('Existing shell changed; review required')
        html=html.replace(before,after)
    # Hidden device controls remain for layout binding compatibility, but carry
    # no fixture IDs/times and never get handlers or a query capability.
    html=html.replace('设备 01 · 已对齐','设备未接入').replace('12:01:33Z +7s → 12:01:40Z','未载入').replace('转到 T+100 查看原始记录','无可用动作').replace('设备 02 · 时间未核实','设备未接入')
    with output.open('x',encoding='utf-8') as f:f.write(html)
    return html

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    build(p.parse_args().output)
