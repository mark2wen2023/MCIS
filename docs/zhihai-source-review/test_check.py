"""Handmade byte maps only; no application imports, real files or runtime calls."""
import csv
from copy import deepcopy
import io
from pathlib import Path
import runpy
import unittest

n=runpy.run_path(str(Path(__file__).with_name('check.py')))
receipt=list(csv.DictReader(io.StringIO(Path(__file__).with_name('review.tsv').read_text()),delimiter='\t'))

class Checks(unittest.TestCase):
    def fixture(self):
        rows=[];recs=[];objects={}
        for index,original in enumerate(receipt):
            path=original['path'];raw=b'pass\n' if path.endswith('.py') else b'synthetic source\n'
            blob=f'{index:040x}';record=dict(original,source_sha256=n['digest'](raw),source_bytes=str(len(raw)),source_blob=blob,previous_sha256=n['digest'](raw))
            objects[(n['SOURCE'],path)]=(raw,blob);objects[(n['PREVIOUS'],path)]=(raw,blob)
            if path not in n['EXTRA']:
                rows.append(dict(path=path,sha256=n['digest'](raw),size=len(raw),blob=blob))
                objects[(n['FROZEN'],path)]=(raw,blob);record.update(comparison='unchanged',old_sha256=n['digest'](raw))
            else:record.update(comparison='additional-review',old_sha256='-')
            recs.append(record)
        calls=[]
        def read(ref,path,optional=False):
            calls.append((ref,path));return objects.get((ref,path)) if optional else objects[(ref,path)]
        return rows,recs,objects,read,calls
    def test_known_bytes_only(self):
        rows,recs,objects,read,calls=self.fixture()
        self.assertEqual(n['verify'](rows,recs,read),dict(unchanged=58,changed=0,**{'additional-review':7}))
        self.assertEqual({p for _,p in calls},{r['path'] for r in recs})
    def test_missing_extra_duplicate(self):
        for transform in (lambda r:r[:-1],lambda r:r+[r[0]],lambda r:r[:-1]+[dict(r[-1],path='unreviewed.py')]):
            rows,recs,_,read,calls=self.fixture()
            with self.assertRaises(n['Rejected']):n['verify'](rows,transform(recs),read)
            self.assertEqual(calls,[])
    def test_changed_bytes_and_wrong_labels(self):
        for field,value in [('source_sha256','0'*64),('previous_sha256','0'*64),('old_sha256','0'*64),('source_bytes','999'),('source_blob','f'*40),('comparison','changed')]:
            rows,recs,_,read,_=self.fixture();r=next(x for x in recs if x['comparison']=='unchanged');r[field]=value
            with self.assertRaises(n['Rejected']):n['verify'](rows,recs,read)
    def test_old_manifest_and_path_rejection(self):
        with self.assertRaises(n['Rejected']):n['old_rows'](b'{}')
        for path in ('../source.py','/tmp/source.py','service/seed.py','image.wav','a//b.py'):
            with self.assertRaises(n['Rejected']):n['safe_path'](path)
    def test_symlink_git_entry_and_unfixed_ref(self):
        g=n['GitObjects'](Path('.'));g.run=lambda *args:b'120000 blob '+b'1'*40+b'\tallowed.py\0'
        with self.assertRaises(n['Rejected']):g.read(n['SOURCE'],'allowed.py')
        g.run=lambda *args:(_ for _ in ()).throw(AssertionError('must not read'))
        with self.assertRaises(n['Rejected']):g.read('main','allowed.py')

if __name__=='__main__':unittest.main()
