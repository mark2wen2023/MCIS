"""Keep complex synthetic demo refusal explicit; never prune unsupported state."""
import hashlib
from sqlalchemy import inspect,text
from .conftest import C,H


def state(app):
    with app.state.db.session() as s:
        rows={name:sorted(repr(tuple(row)) for row in s.execute(text('SELECT * FROM "'+name.replace('"','""')+'"')))
              for name in inspect(s.connection()).get_table_names()}
    root=app.state.settings.blob_dir
    files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in root.rglob('*') if p.is_file()}
    return rows,files


def test_complex_seed_refuses_archive_without_partial_package_or_changes(client,app):
    before=state(app)
    response=client.get(C+'/export',headers=H('LeadInvestigator'))
    assert response.status_code==409,response.text
    assert response.json()['code']=='ARCHIVE_RESTORE_UNSUPPORTED'
    assert response.headers['content-type'].startswith('application/json')
    assert not response.content.startswith(b'PK')
    assert 'content-disposition' not in response.headers
    assert state(app)==before


def test_complex_seed_default_audit_and_export_denials_remain(client,app):
    before=state(app)
    for endpoint in ('/audit','/export'):
        response=client.get(C+endpoint,headers=H())
        assert response.status_code==403,response.text
        assert response.json()['code']=='FORBIDDEN'
    assert state(app)==before
