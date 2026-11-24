"""Long synthetic DOCX, structural checks; optional local layout artifact."""
import argparse
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import export_report, W, text

def run(output=None):
    sentences = [{'sentenceId':f'syn-{i:03d}', 'status':'Draft', 'missing':True,
        'textZh':f'合成记录 {i:03d}：待核；来源未提供。' + '这是用于分页检查的虚构文字。' * 12,
        'textEn':f'Synthetic record {i:03d}: pending verification; source not provided. ' + 'Fictional layout test only. ' * 20,
        'citations':[]} for i in range(80)]
    report = {'reportId':'SYN-LONG-DOCX','caseId':'SYN-XREPO-001','version':1,
        'templateId':'imo-cic','status':'Draft','isFictionalDemo':True,
        'sections':[{'sectionId':'synthetic','titleZh':'合成长表','titleEn':'Synthetic long table',
        'status':'Draft','missing':True,'sentences':sentences}]}
    before = deepcopy(report)
    raw = export_report(report, format='docx', lang='bilingual', include_glossary=True)
    assert report == before
    with ZipFile(BytesIO(raw)) as z:
        assert z.testzip() is None
        body = ET.fromstring(z.read('word/document.xml'))
    tables = body.findall('.//' + W + 'tbl')
    assert len(tables) == 2
    expected = [('中文','English'), ('中文（项目译文）','English')]
    for table, titles in zip(tables, expected, strict=True):
        rows = table.findall(W+'tr')
        assert len(rows) > 1
        assert tuple(text(c) for c in rows[0].findall(W+'tc')) == titles
        assert len(rows[0].findall(W+'trPr/'+W+'tblHeader')) == 1
        assert all(not row.findall('.//'+W+'tblHeader') for row in rows[1:])
    rows = tables[0].findall(W+'tr')
    assert len(rows) == 81
    for row, sentence in zip(rows[1:], sentences, strict=True):
        assert [text(c) for c in row.findall(W+'tc')] == [sentence['textZh'],sentence['textEn']]
    assert 'DRAFT 草稿' in text(body) and 'CONFIRMED 已确认' not in text(body)
    assert '含缺数据项 / Contains missing data' in text(body)
    if output is not None:
        with output.open('xb') as f: f.write(raw)
    print('PASS: tables=2 headerRows=2 contentRowsUnmarked=true bilingualRows=80 inputUnchanged=true layoutVerified=false')

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path)
    run(p.parse_args().output)
