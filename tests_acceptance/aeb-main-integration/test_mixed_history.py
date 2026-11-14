"""Real local API proof that the advertised excluded combination stays refused."""
from tests.test_track_history import client,setup,request,B
from tests.test_working_record_archive import snapshot


def test_actual_track_import_plus_report_timeline_refuses_without_loss(tmp_path):
    with client(tmp_path/'source') as c:
        body=setup(c)
        request(c,'post',B+'/track-imports:commit',body)
        request(c,'post',B+'/reports',{'templateId':'cn-msa','lang':'en'},201)
        request(c,'post',B+'/timeline/events',{'timeSec':1,'kind':'Event','title':'Synthetic mixed history event'},201)
        before=snapshot(c)
        root=c.app.state.settings.blob_dir
        originals={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        failed=request(c,'get',B+'/export',status=409)
        assert failed.json()['code']=='ARCHIVE_RESTORE_UNSUPPORTED'
        assert snapshot(c)==before
        assert {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}==originals
