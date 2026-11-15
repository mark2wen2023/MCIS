"""Developer-only public sample renderer; run from service with PYTHONPATH=.
Writes a new temporary directory; never uses production case storage.
"""
from pathlib import Path
import argparse
import tempfile
import json
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from tests.conftest import make_settings
from tests.test_report_sentence_source_status import create,checked,BASE,HEADERS
parser=argparse.ArgumentParser()
parser.add_argument('--parent', default=None, help='Optional parent for a fresh temporary output directory')
args=parser.parse_args()
out=Path(tempfile.mkdtemp(prefix='mcis-public-pdf-', dir=args.parent))
print(out)
with TestClient(create_app(make_settings(out/'case-storage'))) as c:
 r=create(c)
 (out/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
 p=BASE+'/reports/'+r['reportId']
 for fmt in ['pdf','docx']:
  response=c.get(p+'/export?format='+fmt+'&lang=bilingual',headers=HEADERS)
  assert response.status_code==200,response.text
  (out/('public-report.'+fmt)).write_bytes(response.content)
 assert checked(c,'get',p)==r
