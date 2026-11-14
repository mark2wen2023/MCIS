"""Independent synthetic API/SQLite archive compatibility probes."""
import json
import pytest
from sqlalchemy import text
from tests.test_report_timeline_archive import populate,exported,rewrite,commit,rows,PATH
from tests.test_working_record_archive import client_at,checked,CID,ROOT,HEAD,snapshot

@pytest.mark.parametrize('mutation',['capitalized-path','version-bool','extra-row-field','working-v2','duplicate-reference'])
def test_additional_malformed_extensions_reject_before_write(tmp_path,mutation):
    with client_at(tmp_path/'source',True) as source:
        populate(source);raw=exported(source)
    def change(files,manifest):
        data=json.loads(files[PATH])
        if mutation=='capitalized-path':files['Timeline/records.v1.json']=files.pop(PATH);return
        if mutation=='version-bool':data['version']=True
        if mutation=='extra-row-field':data['events'][0]['unknown']='not discarded'
        if mutation=='working-v2':
            working=json.loads(files['working-records/backup.v1.json']);working['version']=2
            files['working-records/backup.v1.json']=json.dumps(working).encode()
        if mutation=='duplicate-reference':data['events'][0]['doc']['evidenceIds']=['EV-999','EV-999']
        files[PATH]=json.dumps(data).encode()
        files['analysis/timeline.json']=json.dumps({'events':[row['doc'] for row in data['events']]}).encode()
    malformed=rewrite(raw,change)
    with client_at(tmp_path/'target') as target:
        before=snapshot(target);commit(target,malformed,422)
        assert snapshot(target)==before and rows(target)==[]
        assert not(target.app.state.settings.blob_dir/CID).exists()


def test_unknown_case_table_still_refuses_and_rollback_has_no_audit(tmp_path):
    with client_at(tmp_path/'source',True) as source:
        populate(source)
        with source.app.state.db.session() as session:
            session.execute(text('CREATE TABLE synthetic_unclassified (case_id TEXT, body TEXT)'))
            session.execute(text('INSERT INTO synthetic_unclassified VALUES (:c,:b)'),{'c':CID,'b':'synthetic'})
        before=snapshot(source)
        checked(source,'get',ROOT+'/export',status=409)
        assert snapshot(source)==before


def test_confirmed_and_draft_flags_survive_as_original_values(tmp_path):
    with client_at(tmp_path/'source',True) as source:
        populate(source)
        checked(source,'post',ROOT+'/timeline/events',{'timeSec':3.0001,'kind':'Observation','title':'Synthetic historical flag','confirmed':True,'presumptive':True},201)
        before=rows(source);raw=exported(source)
    with client_at(tmp_path/'target') as target:
        commit(target,raw);assert rows(target)==before
        values=[item[3] for item in rows(target)]
        assert {d.get('confirmed') for d in values}=={True,False}
        assert any(d.get('presumptive') is True for d in values)
        assert json.loads(__import__('mcis_service.package.mcase',fromlist=['read_zip']).read_zip(exported(target))['manifest.json'])['packageVersion']=='1.4.0'
