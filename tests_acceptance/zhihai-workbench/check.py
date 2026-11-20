"""Source/markup and synthetic static artifact checks, NOT pixel/browser review."""
import hashlib
from pathlib import Path
import re
import runpy
import subprocess
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[2]
P=runpy.run_path(str(ROOT/'tools/zhihai_workbench_preview/build.py'))
BASE='15dd6143377e345bcbd82b1c5751bf7a565f50b7'
def old(path):return subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True)
def inline(html):return re.findall(r'<script>([\s\S]*?)</script>',html)
class Checks(unittest.TestCase):
    def test_workbench_behavior_unchanged(self):
        path='service/mcis_service/local_review_pilot/workbench.html'
        self.assertEqual(inline((ROOT/path).read_text()),inline(old(path)))
    def test_shaped_image_behavior_and_ids_unchanged(self):
        import ast
        scope={}
        for path,names in [('service/mcis_service/_review_page.py',{'_review_page'}),('service/mcis_service/local_review_pilot/pages.py',{'image_page'})]:
            nodes=[n for n in ast.parse(old(path)).body if isinstance(n,ast.FunctionDef) and n.name in names]
            exec(compile(ast.Module(body=nodes,type_ignores=[]),'<old pure shaper>', 'exec'),scope)
        raw=(ROOT/'service/mcis_service/image_review/review.html').read_text()
        previous=scope['image_page'](raw);current=P['shapes']()[1]
        self.assertEqual(inline(current),inline(previous))
        self.assertEqual(set(re.findall('id="([^"]+)"',current)),set(re.findall('id="([^"]+)"',previous)))
        self.assertIn('<section hidden inert class="image-pane"',current)
        self.assertIn('<details data-task-controls hidden inert>',current)
        # Actual page return/download/task checks are in pilot-pages, not inferred here.
    def test_reference_dimensions_and_semantic_regions(self):
        for html in P['shapes']():
            for value in ['#0c1219','#111a24','#182430','#4dd0e1','#2a3a4d','height:48px','240px minmax(0,1fr) 380px','height:46px','max-width:640px']:
                self.assertIn(value,html)
            self.assertIn('class="side"',html);self.assertIn('class="inspector"',html);self.assertIn('class="stage-bar"',html)
            self.assertIn('尚未',html)
            self.assertNotRegex(html,r'https?://|fonts.googleapis|<iframe')
    def test_static_previews_have_no_active_or_external_content(self):
        files=P['snapshots']();self.assertEqual(len(files),3)
        for html in files.values():
            P['DOM'](html)  # balanced markup and no duplicate IDs
            self.assertNotRegex(html,r'<script\b|\son\w+=|\shref=|\ssrc=|https?://')
            self.assertIn("default-src 'none'",html);self.assertIn('纯合成静态预览',html)
            self.assertNotIn('localStorage',html)
        self.assertIn('SYN-PREVIEW-A',files['02-workbench-selected.html'])
        self.assertIn('未发生保存',files['03-image-review.html'])
    def test_new_owned_output_and_archive_allowlist(self):
        with tempfile.TemporaryDirectory() as root:
            target=Path(root)/'preview';archive=P['build'](target)
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(set(z.namelist()),{'01-workbench-empty.html','02-workbench-selected.html','03-image-review.html','README.txt','SHA256SUMS'})
                for line in z.read('SHA256SUMS').decode().splitlines():
                    sha,name=line.split('  ');self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),sha)
            with self.assertRaises(FileExistsError):P['build'](target)
if __name__=='__main__':unittest.main()
