"""Explicit local static display of replay-validated public research snapshots."""
import argparse
from html import escape
import sys
from research.expert_meeting.citations import citation_view
from research.expert_meeting.machine import MAX_SNAPSHOT
from research.expert_meeting.review_plan import review_plan

PHASES = {'ready':'尚未开始', 'round_open':'本轮尚未完整', 'round_review':'本轮已收齐，仍未核实',
          'completed_unverified':'协议轮次已完成，意见仍未核实', 'stopped_by_operator':'人工停止',
          'stopped_failed':'因失败停止', 'stopped_unknown':'因结果未知停止', 'timed_out':'已超时'}


def render(snapshot):
    view = citation_view(snapshot)  # Do not accept caller-supplied projection flags.
    def text(value): return escape(str(value), quote=True)
    parts = ['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<title>公开片段专家意见｜离线审阅</title>',
             '<style>body{max-width:72rem;margin:2rem auto;padding:0 1rem;font:1rem/1.65 system-ui;color:#182333;background:#f6f8fa}article,section{background:white;border:1px solid #64748b;padding:1rem;margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}dt{font-weight:bold}dd{margin:0 0 1rem}code{overflow-wrap:anywhere}h1,h2,h3{line-height:1.3}</style></head><body><main>',
             '<h1>公开片段专家意见：离线审阅</h1>',
             '<p><strong>未核实研究意见；不证明真实模型执行、作者身份、语义支持或案件事实。</strong></p>',
             '<p>三条人工测试主张（含反例）均来自同一份报告的同一页，不构成三个独立来源。定位匹配不代表主张成立。</p>',
             '<section><h2>会议状态</h2>',
             '<p>'+text(PHASES[view['phase']])+'</p>',
             '<p>模式：'+('脚本模拟声明' if view['mode']=='simulation_only' else '远端协议声明（不证明调用）')+'</p>',
             '<p>会议标识：<code>'+text(view['meetingId'])+'</code></p>',
             '<p>快照 SHA-256：<code>'+text(view['snapshotSha256'])+'</code></p>',
             '<p>公开片段包 SHA-256：<code>'+text(view['packetSha256'])+'</code></p></section>']
    if not view['rows']:
        parts.append('<p>没有已接受的意见；未生成替代回答。</p>')
    for row in view['rows']:
        loc = row['source']['locator']; fixed = row['fixedReportCitation']; selected = row['reviewerSelectedCitation']
        parts += ['<article><h2>第 '+text(row['round'])+' 轮 · '+text(row['roleId'])+' · '+text(row['itemId'])+'</h2>',
                  '<p>未核实；来源声明：'+text(row['declaredResponseSource'])+'；席位：'+text(row['ticketId'])+'</p><dl>']
        fields = [('人工编写测试主张（含反例）',row['claim']['text']),
                  ('审读者声明标签（不是事实裁定）',row['declaredLabel']),
                  ('意见理由',row['rationale']),('不确定性',row['uncertainty']),
                  ('固定报告引文',fixed['quote']),('审读者选取引文',selected['quote'])]
        for label,value in fields:
            parts.append('<dt>'+text(label)+'</dt><dd><pre>'+text(value)+'</pre></dd>')
        parts += ['</dl><p>选取引文定位：'+text(selected['locationStatus'])+'；共 '+text(selected['occurrenceCount'])+' 处。偏移单位为 Unicode 码点，不是字节或 UTF-16。</p>',
                  '<p>位置（起点，长度）：'+text([(x['start'],x['length']) for x in selected['locations']])+'</p>']
        if selected['locationsTruncated']: parts.append('<p>位置列表已截断；不能将列表当成全部位置。</p>')
        parts += ['<p>固定引文位置：'+text((fixed['start'],fixed['length']))+'</p>',
                  '<h3>报告出处声明（未经独立认证）</h3><p>PDF 页 '+text(loc['pdfPage'])+' / 印刷页 '+text(loc['printedPage'])+'；'+text(loc['section'])+'</p>',
                  '<p>来源 URL（仅文本，不访问）：<code>'+text(loc['url'])+'</code></p>',
                  '<p>PDF SHA-256：<code>'+text(loc['pdfSha256'])+'</code></p>',
                  '<p>片段 SHA-256：<code>'+text(row['source']['sha256'])+'</code></p>',
                  '<details><summary>冻结报告片段全文</summary><pre>'+text(row['source']['text'])+'</pre></details></article>']
    parts.append('<section><h2>并列意见关系</h2>')
    if not any(view['comparison']): parts.append('<p>尚无完整一轮可供对照；不推断缺席方意见。</p>')
    for index, comparison in enumerate(view['comparison'],1):
        for item in comparison:
            meaning = '标签相同，但不是共识' if item['relationship']=='same_labels_not_consensus' else '标签不同，分歧未解决'
            parts.append('<p>第 '+text(index)+' 轮 · '+text(item['itemId'])+'：'+meaning+'；'+text(item['labels'])+'</p>')
    parts.append('</section><section><h2>人工复核问题清单（全部待复核）</h2>')
    plan = review_plan(snapshot)
    parts.append('<p>仅列当前轮次待办；历史意见保留在上方。自动生成问题不等于已完成人工审查，不认证审查人。</p>')
    for task in plan['tasks']:
        parts.append('<h3>'+text(task['itemId'])+' · 当前轮次 '+text(task['round'])+'</h3>')
        parts.append('<p>人工测试主张（含反例）：'+text(task['claim'])+'</p>')
        parts.append('<p>快照绑定任务标识：<code>'+text(task['taskId'])+'</code></p>')
        parts.append('<p>尚缺意见角色：'+text(', '.join(task['missingRoles']) or '无；仍需人工复核')+'</p><ul>')
        for question in task['questions']: parts.append('<li>'+text(question)+'</li>')
        parts.append('</ul>')
    parts.append('</section><p>本页没有模型运行、上传、批准或案件写入功能。静态 HTML 本身不是签名凭证；修改后应重新验证原始快照。</p></main></body></html>')
    return ''.join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-stdin', required=True, action='store_true')
    parser.parse_args(argv)
    try:
        html = render(sys.stdin.buffer.read(MAX_SNAPSHOT + 1))
    except Exception:
        print('Snapshot rejected; no HTML generated.', file=sys.stderr)
        return 2
    sys.stdout.buffer.write(html.encode('utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
