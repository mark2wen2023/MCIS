"""Only handmade generation documents; no application imports or storage."""
from copy import deepcopy
import json
from pathlib import Path
import runpy
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
parse = runpy.run_path(str(ROOT/'service/mcis_service/reports/generation_snapshot.py'))['generation_sentence']
validator = Draft202012Validator(json.loads((ROOT/'contracts/schemas/report.schema.json').read_text()))
def validate(name, doc):
    assert name == 'report'
    validator.validate(doc)

def report(rid, version, text, parent=None):
    sentence = dict(sentenceId='sentence-synthetic', status='Draft', source='Generated',
                    textZh=text, textEn=text, generatedText=dict(textZh=text, textEn=text),
                    reviewedBy=None, reviewedAt=None, reviews=[], missing=False, citations=[])
    section = dict(sectionId='section-synthetic', titleZh='合成', titleEn='Synthetic',
                   dataSources=[], sentences=[sentence], **{k:deepcopy(v) for k,v in sentence.items()
                   if k not in ('sentenceId', 'citations')})
    return dict(reportId=rid, familyId='RPT-'+'1'*20, parentReportId=parent,
                caseId='CASE-SYNTHETIC', templateId='imo-cic', lang='bilingual', version=version,
                status='Draft', isFictionalDemo=True, realDataStatus='fictional', createdBy='synthetic',
                createdUtc='2026-01-01T00:00:00Z', sections=[section], disclaimerZh='合成',
                disclaimerEn='Synthetic', reportHref='#/report?case=CASE-SYNTHETIC&report='+rid)

def inputs(doc, number, previous=None):
    sid='RA-'+str(number)*32
    action='report.regenerate' if previous else 'report.generate'
    return dict(snapshot=dict(snapshotId=sid, reportId=doc['reportId'],sectionId=None,sentenceId=None,
                reason='', beforeValue=deepcopy(previous),afterValue=deepcopy(doc),summary='synthetic',auditSeq=number),
                audit_event=dict(seq=number,caseId=doc['caseId'],entityId=doc['reportId'],entityType='report',
                                 category='Report',action=action,snapshotRef='report-snapshot:'+sid))
def read(doc, values):
    return parse(case_id=doc['caseId'],report_id=doc['reportId'],section_id='section-synthetic',
                 sentence_id='sentence-synthetic',validate_contract=validate,**values)

first=report('RPT-'+'1'*20,1,'First synthetic sentence')
a=inputs(first,1)
old=read(first,a)
second=report('RPT-'+'2'*20,2,'Second synthetic sentence',first['reportId'])
b=inputs(second,2,first)
new=read(second,b)
assert old['sentence']['textZh']=='First synthetic sentence'
assert new['sentence']['textZh']=='Second synthetic sentence'
assert old['snapshotId']!=new['snapshotId'] and old['reportId']!=new['reportId']
# A current-row edit and a later generation cannot alter the explicitly selected RA.
first['sections'][0]['sentences'][0]['textZh']='Current edited sentence'
second['sections'][0]['sentences'][0]['textZh']='Current second edited sentence'
assert read(first,a)==old and read(second,b)==new
# Returned copy is independent of its input and subsequent callers.
old['sentence']['textZh']='Consumer local edit'
assert read(first,a)['sentence']['textZh']=='First synthetic sentence'
assert not new['persistentBinding'] and not new['sourceVerified']
print('PASS: two synthetic generations, current-row isolation, returned-copy isolation')
