"""Real synthetic DB query -> production shared-shell JS under a fake DOM.
No HTTP/real browser. Model payload is temporary and never committed to Git.
"""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
base=runpy.run_path(str(HERE/'business.py'))
PRODUCT='db90fdf73de7bd26ba75819f0102fc03d0789faf'
PATHS=base['PATHS']+('service/mcis_service/trajectory_exchange/registered_query.py',)

class UI:
    def test_real_model_to_production_adapter(self):
        from mcis_service.trajectory_exchange.registered_query import _query_registered_pair
        times=['2026-02-01T12:00:20.000Z','2026-02-01T12:01:20.000Z','2026-02-01T12:01:40.000Z','2026-02-01T12:02:04.250Z']
        frames=[_query_registered_pair(self.ctx,self.cid,self.pins,'Synthetic UI model',t) for t in times]
        root=HERE.parents[1]
        builder=runpy.run_path(str(root/'tools/replay_evidence_workbench/registered_build.py'))
        page=self.root/'adapter.html';builder['build'](page)
        models=self.root/'models.json';models.write_text(json.dumps(frames))
        subprocess.run(['node',str(HERE/'ui.cjs'),str(page),str(models)],check=True)
        self.assertEqual(self.counts(),(2,10,10))

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I')
    with tempfile.TemporaryDirectory(prefix='mcis-registered-ui-') as folder:
        source=base['materialize'](Path(folder),ref=PRODUCT,paths=PATHS)
        ok=base['run'](source,extra_cases=(UI,),allowed_paths=PATHS)
    raise SystemExit(0 if ok else 1)
