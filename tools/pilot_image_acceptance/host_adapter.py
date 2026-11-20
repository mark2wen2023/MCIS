"""UNEXECUTED owned-resource adapter; no launcher or isolation implementation.

Only an approved external host can supply isolated_workspace(). Its context
must inspect/enforce mount/network/source/credential exclusions BEFORE yielding
an exclusive writable parent. A path/boolean from a browser is not this host.
No platform adapter is supplied here: absent host fails before app/ORM imports.
"""
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from .authority import CreationAuthority, CreationAdapter
from .prepare import checked


@contextmanager
def owned_creation_scope(*, authority, approved_host=None, sessions=None, origin=None):
    checked(type(authority) is CreationAuthority, 'Creation authority required')
    checked(approved_host is not None and callable(getattr(approved_host,'isolated_workspace',None)),
            'No approved mount/network/source isolation host; execution blocked')
    authority.claim()
    # External host must reject unverified environments, not merely attest True.
    with approved_host.isolated_workspace() as parent:
        checked(isinstance(parent,Path) and parent.is_absolute(), 'Host must supply private absolute workspace')
        with TemporaryDirectory(prefix='mcis-creation-',dir=parent) as temporary:
            root=Path(temporary);db_path=root/'pilot.sqlite3';blobs=root/'blobs';blobs.mkdir()
            checked(not db_path.exists(), 'Refuse existing database')
            from mcis_service.db import Database
            from mcis_service.local_review_pilot.factory import create_local_review_pilot
            from mcis_service.common.context import Ctx
            from fastapi import Request
            from sqlalchemy import inspect, text
            db=Database('sqlite:///'+str(db_path))
            adapter=None
            try:
                app=create_local_review_pilot(enabled=True,db=db,sessions=sessions,origin=origin,
                        image_imports=True,image_blob_dir=blobs,evidence_registration=True)
                expected={'cases','evidence_items','custody_events','audit_events','access_policies',
                          'archive_import_history','image_ocr_review_records'}
                checked(set(inspect(db.engine).get_table_names())==expected,'Unexpected preparation schema')
                # Only fixed identifiers, no arbitrary SQL/client-provided table.
                with db.engine.connect() as connection:
                    for name in sorted(expected):
                        checked(connection.execute(text('SELECT COUNT(*) FROM '+name)).scalar_one()==0,
                                'Preparation requires exclusively new empty storage')
                adapter=CreationAdapter(authority,app,Ctx,Request)
                yield adapter, app, root
            finally:
                if adapter is not None:adapter.close()
                db.engine.dispose()
                # TemporaryDirectory then removes only this adapter's own root.
                # No listener/browser is started here. Their lifecycle and session
                # revocation must remain inside the external host's outer scope.


if __name__ == '__main__':
    raise SystemExit('BLOCKED: approved isolation host, verified server config and session bootstrap absent; nothing started')
