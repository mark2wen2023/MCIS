"""Explicit offline research-note template and export. Never an official review."""
import argparse
import json
import os
import sys
from evaluate import load, evaluate, exact, sha, ident, array
from render_review import render, esc

STATUS = 'unverified_research_notes_not_case_facts'
MAX_OUTPUT = 9 * 1024 * 1024
FLAGS = ('timeAssociationNeedsCheck', 'sourceAssociationNeedsCheck', 'otherNeedsCheck')


def template(corpus, corpus_sha, predictions, prediction_sha):
    result = evaluate(corpus, corpus_sha, predictions)
    sha(prediction_sha)
    return {'schemaVersion': 1, 'status': STATUS, 'corpusSha256': corpus_sha,
            'predictionsSha256': prediction_sha,
            'items': [{'itemId': item['itemId'], **{flag: False for flag in FLAGS}, 'note': ''}
                      for item in result['items']]}


def validate_worksheet(worksheet, expected):
    exact(worksheet, 'schemaVersion status corpusSha256 predictionsSha256 items')
    if type(worksheet['schemaVersion']) is not int or worksheet['schemaVersion'] != 1:
        raise ValueError('version')
    for field in ('status', 'corpusSha256', 'predictionsSha256'):
        if worksheet[field] != expected[field]:
            raise ValueError('binding')
    wanted = {item['itemId'] for item in expected['items']}
    notes = {}
    for item in array(worksheet['items'], 1, 100):
        exact(item, 'itemId timeAssociationNeedsCheck sourceAssociationNeedsCheck otherNeedsCheck note')
        key = ident(item['itemId'])
        if key not in wanted or key in notes:
            raise ValueError('item binding')
        for flag in FLAGS:
            if type(item[flag]) is not bool:
                raise ValueError('flag')
        note = item['note']
        if type(note) is not str or len(note) > 4000:
            raise ValueError('note')
        note.encode('utf-8')
        if any(item[flag] for flag in FLAGS) and not note.strip():
            raise ValueError('reason required')
        notes[key] = dict(item)
    if set(notes) != wanted:
        raise ValueError('coverage')
    return notes


def export(corpus, corpus_sha, predictions, prediction_sha, worksheet, worksheet_sha):
    expected = template(corpus, corpus_sha, predictions, prediction_sha)
    notes = validate_worksheet(worksheet, expected)
    sha(worksheet_sha)
    base = render(corpus, corpus_sha, predictions).decode('utf-8')
    # Original model, quotes and source declarations remain unchanged. Editable controls
    # in the original research sheet remain temporary; this appended snapshot is text only.
    parts = ['<section id="exported-research-notes"><h1>显式导出的研究备注快照</h1>',
             '<p class="notice">此文件包含本次从本地 JSON 表读取的备注快照。不是已认证调查员意见，不是正式审核，不是案件事实，不写入任何案件系统。文件可被编辑；摘要仅供对照，不是签名或真实性证明。上方临时控件的修改不会自动进入此快照。</p>',
             '<p>所有未勾选项仅表示未标记，不能解读为已核实、已同意或无问题。备注来源为用户提供的本地文件，本工具不识别作者，也不判断备注是否正确。</p>',
             '<p>语料 SHA256：'+esc(corpus_sha)+'<br>模型输出文件 SHA256：'+esc(prediction_sha)+'<br>备注文件 SHA256：'+esc(worksheet_sha)+'</p>']
    names = dict(zip(FLAGS, ('时间关联需核实', '来源关联需核实', '其他解释问题')))
    for index, item in enumerate(expected['items'], 1):
        row = notes[item['itemId']]
        parts.append('<article><h2>备注第 '+str(index)+' 项 · '+esc(row['itemId'])+'</h2>')
        for flag in FLAGS:
            parts.append('<p>'+names[flag]+'：'+('标记待核实' if row[flag] else '未标记（不表示核实通过）')+'</p>')
        parts.append('<h3>原样备注（未经认证）</h3><pre>'+esc(row['note'])+'</pre></article>')
    parts.append('</section>')
    base = base.replace('<body>', '<body><p class="notice">已生成本地研究备注快照，见文末。下方复核页的输入框仍为临时控件，不会自动修改已导出备注。</p>')
    output = base.replace('</body>', ''.join(parts)+'</body>').encode('utf-8')
    if len(output) > MAX_OUTPUT:
        raise ValueError('budget')
    return output


def write_new(path, content):
    # Explicitly chosen local file only; never overwrite an existing file/symlink.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as target:
        target.write(content)
        target.flush()
        os.fsync(target.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('template', 'export'))
    parser.add_argument('--corpus', required=True)
    parser.add_argument('--predictions', required=True)
    parser.add_argument('--worksheet')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    corpus, corpus_sha = load(args.corpus)
    predictions, prediction_sha = load(args.predictions)
    if args.action == 'template':
        if args.worksheet is not None:
            raise ValueError('unexpected worksheet')
        content = json.dumps(template(corpus, corpus_sha, predictions, prediction_sha), ensure_ascii=False, indent=2).encode('utf-8')
    else:
        if args.worksheet is None:
            raise ValueError('worksheet required')
        worksheet, worksheet_sha = load(args.worksheet)
        content = export(corpus, corpus_sha, predictions, prediction_sha, worksheet, worksheet_sha)
    write_new(args.output, content)
    print(json.dumps({'ok': True, 'fileWritten': True, 'caseUpdated': False,
                      'reviewerAuthenticated': False, 'modelCalled': False}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('{"ok":false,"errorCode":"RESEARCH_NOTES_EXPORT_REJECTED"}', file=sys.stderr)
        sys.exit(2)
