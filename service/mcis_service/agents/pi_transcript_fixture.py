"""Explicit fixed fictional Pi tool host, temporary SQLite, no model/network."""
import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path
from ..config import Settings
from ..db import Database, put_doc
from ..identity.demo import prepare, CASE
from ..interviews.models import InterviewRow
from ..common import contracts
from ..investigation.fixture_host import Lines, output
from ..investigation.http_trial import pairs, invalid
from .extraction_review_fixture import document, RECORD
from .host_extraction import describe
from .pi_transcript_host import TranscriptHost

async def run():
    with tempfile.TemporaryDirectory(prefix='mcis-pi-transcript-') as directory:
        root = Path(directory)
        settings = Settings(data_dir=root, db_url=f'sqlite:///{root/"fixture.db"}',
                            seed_demo=False, core_cmd='unused', host='127.0.0.1', port=0)
        settings.blob_dir.mkdir(parents=True)
        db = Database(settings.resolved_db_url)
        host = None
        try:
            db.create_all()
            token = await prepare(db, settings)
            doc = document()
            contracts.validate('interview', doc)
            with db.session() as s:
                put_doc(s, InterviewRow, CASE, RECORD, doc)
            args = (db, settings, token, CASE, RECORD)
            host = TranscriptHost(*args, describe(*args)['bindingDigest'])
            del token, args
            output({'ready': True, 'fixture': True})
            lines = Lines()
            deadline = time.monotonic() + 120
            for _ in range(32):
                raw = lines.read(min(deadline, time.monotonic() + 30))
                if raw is None:
                    return
                value = json.loads(raw.decode(), object_pairs_hook=pairs, parse_constant=invalid)
                output(host.dispatch(value))
                if value.get('op') == 'final':
                    return
        finally:
            if host is not None:
                host.close()
            db.engine.dispose()

def main():
    if len(sys.argv) != 1:
        return 2
    try:
        asyncio.run(run())
        return 0
    except (Exception, KeyboardInterrupt):
        print('Fictional Pi host stopped without a confirmed result.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
