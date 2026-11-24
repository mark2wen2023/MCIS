"""A standalone report must identify which original excerpt each citation refers to."""
import copy
import subprocess
import pytest
from docx import Document
from mcis_service.reports.exporter import export_report

fixed={'kind':'evidence','id':'SYN-EV-01','href':'/cases/SYN-ONLY/evidence/SYN-EV-01','needsReview':True}
a={**fixed,'sourceRef':'SYN-PAGE-02 LINES-011-014'}
b={**fixed,'sourceRef':'SYN-PAGE-05 LINES-042-045'}
c={**fixed,'id':'SYN-EV-02','href':'/cases/SYN-ONLY/evidence/SYN-EV-02','sourceRef':'SYN-PAGE-03 LINES-019-021'}
u={**fixed,'id':'SYN-EV-03','href':'/cases/SYN-ONLY/evidence/SYN-EV-03','sourceRef':'未知段落 UNSPECIFIED','unregistered':True}
def row(n,zh,en,source,citations):
    return dict(sentenceId=n,textZh=zh,textEn=en,status='Draft',source=source,citations=citations)
sections=[
 dict(titleZh='第一章',titleEn='Section One',status='Draft',sentences=[
    row('one','甲段船首向记录','Alpha source','Generated',[a,c]),
    row('two','乙段经调查员合成改写','Bravo edited','Investigator',[b])]),
 dict(titleZh='第二章',titleEn='Section Two',status='Draft',sentences=[
    row('three','再引甲段','Alpha repeat','Generated',[a,u]),
    row('four','没有引用','No citation','Generated',[])])]
report=dict(caseId='SYN-ONLY',reportId='SYN-LOCATOR',isFictionalDemo=True,version=1,sections=sections)
snap=copy.deepcopy(report)

def compact(s): return ''.join(s.split())
def check(body,refs,lang):
    for text in ('SYN-PAGE-02 LINES-011-014','SYN-PAGE-05 LINES-042-045','SYN-PAGE-03 LINES-019-021','UNSPECIFIED'):
        assert compact(refs).count(compact(text))==1,(lang,text,refs)
    assert compact(body).count('[SYN-EV-01]')== (6 if lang=='bilingual' else 3),(lang,body)
    assert 'needsreview' in compact(body) and 'unregistered' in body
    if lang!='zh': assert 'traceabilityonly' in compact(body)
    if lang!='en': assert '仅用于追溯' in compact(body)
    rt=compact(refs); bt=compact(body)
    for i,line in ((1,'SYN-PAGE-02'),(2,'SYN-PAGE-05')):
        assert f'[SYN-EV-01][R{i:02}]（需复核/needsreview）evidence—/cases/SYN-ONLY/evidence/SYN-EV-01|{line}' in rt,(lang,line,rt)
    for heading,num in (('Alpha source',1),('Bravo edited',2),('Alpha repeat',1),('甲段船首向记录',1),('乙段经调查员合成改写',2),('再引甲段',1)):
        if compact(heading) in bt:
            assert f'{compact(heading)}[SYN-EV-01][R{num:02}]' in bt,(lang,heading,bt)
    assert bt.count('[R01]')==(4 if lang=='bilingual' else 2)
    assert bt.count('[R02]')==(2 if lang=='bilingual' else 1)
    assert rt.count('[R01]')==rt.count('[R02]')==1
    assert '[SYN-EV-02]（' in rt and '[SYN-EV-03]（' in rt

@pytest.mark.parametrize("lang", ["zh", "en", "bilingual"])
@pytest.mark.parametrize("fmt", ["pdf", "docx"])
def test_distinguishes_excerpt_locators_without_changing_evidence_id(tmp_path, lang, fmt):
    p = tmp_path / f"report.{fmt}"
    p.write_bytes(export_report(report, format=fmt, lang=lang))
    if fmt == "pdf":
        text = subprocess.check_output(["pdftotext", "-raw", str(p), "-"]).decode()
        body, refs = text.split("引用表 / References", 1)
    else:
        doc = Document(p)
        text = "\n".join(x.text for x in doc.paragraphs)
        body, refs = text.split("引用表 / References", 1)
        if lang == "bilingual":
            body += "\n" + "\n".join(c.text for table in doc.tables[:2] for row in table.rows for c in row.cells)
    assert "Fictional" in body
    check(body, refs, lang)
    assert report == snap
