"""Named UI source + import-free renderer only; no product app import."""
import ast
import json
from pathlib import Path
import subprocess
import sys
scope = {}
exec(compile(ast.parse(Path('service/mcis_service/_review_page.py').read_text()), '<pure renderer>', 'exec'), scope)
base = sys.argv[1] if len(sys.argv) > 1 else None
if base is not None and base != '3667fa4f63c542d820b41accd4f71a1e0e153818':
    raise ValueError('only fixed baseline allowed')
pages = {}
for media in ['image','audio']:
    path = f'service/mcis_service/{media}_review/review.html'
    html = subprocess.check_output(['git','show',base+':'+path],text=True) if base else Path(path).read_text()
    pages[media] = {mode:scope['_review_page'](html,task_routes=(mode=='full')) for mode in ['full','limited']}
subprocess.run(['node','tests_acceptance/media-case-only/page.cjs'],input=json.dumps(pages),text=True,check=True)
