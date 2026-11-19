"""Pure synthetic dictionaries; load only the import-free-of-application projector."""
import copy
from pathlib import Path
import runpy
ns = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'service/mcis_service/reports/media_reference.py'))
project = ns['project_saved_media']; Error = ns['ProjectionUnavailable']
A='a'*64; B='b'*64; C='c'*64; D='d'*64

def fixture(media):
    if media == 'audio':
        initial={'machineDraft':{'source':{'caseId':'CASE-SYN','evidenceId':'EV-A','currentSha256':A,'registeredSha256':B,'stateDigest':C},'artifactSha256':D,'transcript':{'segments':[{'id':'SEG-SYN'}],'unlocatedSegments':[]}},'draftBytesSha256':C}
        human={'revision':1,'expectedRevision':0,'segmentId':'SEG-SYN','text':'handmade audio text','hearingStatus':'pending','audioSha256':A,'machineArtifactSha256':D,'factVerified':False}
        items=[{'caseId':'CASE-SYN','evidenceId':'EV-A','sha256':B,'currentSha256':A}]
        role='audio'
    else:
        initial={'candidate':{'source':{'pdf_sha256':A,'image_sha256':B,'raw_sha256':C},'text_lines':[{'text':'handmade OCR line'}]},'sourceVersions':{'pdf':{'evidenceId':'EV-A','sha256':A},'image':{'evidenceId':'EV-B','sha256':B},'raw':{'sha256':C,'kind':'task-artifact'},'candidate':{'sha256':D,'kind':'task-artifact'}}}
        human={'revision':1,'expectedRevision':0,'lineIndex':0,'text':'handmade image text','decision':'transcription-checked','factVerified':False}
        items=[{'caseId':'CASE-SYN','evidenceId':'EV-A','currentSha256':A},{'caseId':'CASE-SYN','evidenceId':'EV-B','currentSha256':B}]
        role='pdf'
    rows=[{'case_id':'CASE-SYN','run_id':'RUN-SYN','revision':n,'doc':d} for n,d in [(0,initial),(1,human)]]
    return dict(media=media,case_id='CASE-SYN',run_id='RUN-SYN',revision=1,evidence_id='EV-A',evidence_role=role,saved_rows=rows,evidence_items=items)

def expect(args, code):
    try: project(**args)
    except Error as e: assert e.code==code,(e.code,code)
    else: raise AssertionError('expected '+code)

for media in ('audio','image'):
    a=fixture(media); original=copy.deepcopy(a); out=project(**a)
    assert out['caseId']=='CASE-SYN' and out['revision']==1 and out['evidenceId']=='EV-A'
    assert out['humanText']==a['saved_rows'][1]['doc']['text'] and out['factVerified'] is False
    out['sourceVersions'].clear(); assert a==original
    # Select old exact human revision even when a later saved revision exists.
    newer=copy.deepcopy(a['saved_rows'][1]); newer['revision']=2; newer['doc'].update(revision=2,expectedRevision=1,text='newer')
    a['saved_rows'].append(newer)
    assert project(**a)['humanText']!='newer'
    a['revision']=3; expect(a,'revision_missing')
    a=fixture(media); a['saved_rows']=a['saved_rows'][:1]; expect(a,'no_human_revision')
    for invalid in (None,0,-1,True,'latest',1001):
        a=fixture(media); a['revision']=invalid; expect(a,'invalid_revision')
    a=fixture(media); a['saved_rows'][1]['doc']['revision']=2; expect(a,'revision_mismatch')
    a=fixture(media); a['saved_rows'][1]['case_id']='OTHER'; expect(a,'case_mismatch')
    a=fixture(media); a['evidence_items'][0]['caseId']='OTHER'; expect(a,'case_mismatch')
    a=fixture(media); a['saved_rows'][1]['run_id']='OTHER'; expect(a,'run_mismatch')
    a=fixture(media); a['evidence_id']='OTHER'; expect(a,'evidence_mismatch')
    a=fixture(media); a['saved_rows'].append(copy.deepcopy(a['saved_rows'][1])); expect(a,'ambiguous_revision')
    a=fixture(media); a['evidence_items'][0]['currentSha256']=D; expect(a,'source_changed')
    a=fixture(media); a['evidence_items'][0].pop('currentSha256'); expect(a,'saved_shape_unknown')
    a=fixture(media); a['evidence_items'][0]['currentSha256']=None; expect(a,'source_digest_unknown')
    a=fixture(media); a['saved_rows'][1]['doc'].pop('text'); expect(a,'saved_shape_unknown')
    print('PASS',media,'exact saved version, unchanged inputs, missing/invalid revision, case/run/evidence identity, source mismatch')
a=fixture('image'); a['evidence_items'][1]['currentSha256']=D; expect(a,'source_changed')
a=fixture('image'); a['saved_rows'][0]['doc']['sourceVersions']['image']['sha256']=None; expect(a,'source_digest_unknown')
a=fixture('image'); a['evidence_role']='image'; a['evidence_id']='EV-B'; assert project(**a)['evidenceId']=='EV-B'
a=fixture('audio'); a['saved_rows'][1]['doc']['audioSha256']=B; expect(a,'saved_source_mismatch')
a=fixture('audio'); a['saved_rows'][1]['doc']['segmentId']='ABSENT'; expect(a,'target_missing_or_ambiguous')
a=fixture('audio'); a['saved_rows'][1]['doc'].update(hearingStatus='unintelligible',text=''); assert project(**a)['humanText']==''
print('PASS dual-image source requirement, explicit evidence role, audio revision binding, unintelligible empty text')
print('COMPLETE: synthetic projection only; no application imports, requests, storage or source-byte verification')
