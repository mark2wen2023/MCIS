import importlib.util,importlib.metadata,io,json,sys,tarfile,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('preflight',P/'preflight.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Checks(unittest.TestCase):
    def fixture(self,p,omit=False):
        root=p/'models';root.mkdir();images=p/'images';images.mkdir();name='toy';folder=root/(name+'_infer');folder.mkdir()
        with tarfile.open(root/(name+'.tar'),'w') as tar:
            for f in sorted(m.REQUIRED-({'inference.yml'} if omit else set())):
                b=('controlled toy '+f).encode();(folder/f).write_bytes(b);info=tarfile.TarInfo(name+'_infer/'+f);info.size=len(b);tar.addfile(info,io.BytesIO(b))
        (images/'toy.png').write_bytes(b'controlled non-image fixture')
        return root,images,{name:m.digest(root/(name+'.tar'))},{'toy.png':m.digest(images/'toy.png')}
    def test_positive_never_runtime_ready(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));r=m._check(args[0],args[1],m.PACKAGES.__getitem__,args[2],args[3])
            self.assertTrue(r['staticInputsMatch']);self.assertFalse(r['readyForInference']);self.assertFalse(r['modelImported'])
    def test_missing_packages(self):
        def missing(n):raise importlib.metadata.PackageNotFoundError(n)
        with tempfile.TemporaryDirectory() as d:
            a=self.fixture(Path(d));self.assertEqual(m._check(a[0],a[1],missing,a[2],a[3])['status'],'blocked')
    def test_version_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.fixture(Path(d));self.assertFalse(m._check(a[0],a[1],lambda n:'0.0',a[2],a[3])['staticInputsMatch'])
    def test_changed_archive_extracted_and_image(self):
        for part in ('archive','extracted','image'):
            with tempfile.TemporaryDirectory() as d:
                a=self.fixture(Path(d));f={'archive':a[0]/'toy.tar','extracted':a[0]/'toy_infer/inference.json','image':a[1]/'toy.png'}[part];f.write_bytes(b'changed')
                with self.subTest(part=part):self.assertFalse(m._check(a[0],a[1],m.PACKAGES.__getitem__,a[2],a[3])['staticInputsMatch'])
    def test_missing_member(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.fixture(Path(d),True);self.assertEqual(m.archive_check(a[0],'toy',a[2]['toy']),'required_members_missing')
    def test_missing_files(self):
        with tempfile.TemporaryDirectory() as d:
            r=m._check(Path(d),Path(d),m.PACKAGES.__getitem__,m.MODELS,m.IMAGES);self.assertEqual(r['status'],'blocked')
    def test_no_model_import(self):
        self.assertFalse(any(n.split('.')[0] in ('paddle','paddleocr','paddlex') for n in sys.modules))
if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks));print(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'fixtures':'toy bytes only; not official models or OCR scores'}));sys.exit(0 if r.wasSuccessful() else 1)
