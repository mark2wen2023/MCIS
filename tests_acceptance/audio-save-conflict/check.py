"""Only pure HTML shaping and Node memory fixtures, no application import."""
import ast
from pathlib import Path
import os
import subprocess
import tempfile
scope = {}
exec(compile(ast.parse(Path('service/mcis_service/_review_page.py').read_text()), '<pure renderer>', 'exec'), scope)
html = Path('service/mcis_service/audio_review/review.html').read_text()
with tempfile.TemporaryDirectory(prefix='mcis-picker-source-') as tmp:
    for enabled in [True, False]:
        p = Path(tmp)/'review.html'
        p.write_text(scope['_review_page'](html, task_routes=enabled))
        print('Full' if enabled else 'Limited', flush=True)
        subprocess.run(['node','--test','tests_acceptance/audio-save-conflict/page.test.cjs'], env={**os.environ,'AUDIO_PAGE_SOURCE':str(p)}, check=True)
