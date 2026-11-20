"""Packager checks on hand-created bytes/directories only; no image/app imports."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
P=runpy.run_path(str(ROOT/'tools/pilot_image_build/package.py'))
Blocked=P['Blocked']

def fixture():
    name='tools/pilot_image_acceptance/container_entry.py';raw=b'# fabricated source only\n'
    row={'path':name,'blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
         'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)}
    m={'format':'mcis-pilot-build-inputs/1','commit':'a'*40,'files':[row],'blocked':[],
       'external':{'status':'reviewed','base_image_id':'sha256:'+'b'*64}}
    return m,lambda _:raw

class Checks(unittest.TestCase):
    def test_review_snapshot_never_has_recipe_and_existing_target_refused(self):
        m,reader=fixture();m['blocked']=[{'code':'synthetic missing table'}]
        with tempfile.TemporaryDirectory() as root:
            target=Path(root)/'new'
            result=P['assemble'](m,reader,target,review_only=True)
            self.assertFalse(result['buildable']);self.assertFalse((target/'Dockerfile').exists())
            self.assertEqual((target/'source'/m['files'][0]['path']).read_bytes(),reader(None))
            with self.assertRaises(Blocked):P['assemble'](m,reader,target,review_only=True)

    def test_normal_context_with_only_fabricated_external_bytes(self):
        m,reader=fixture()
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);external=root/'external';external.mkdir()
            for key,name,raw in [('archive','base.oci.tar',b'fake archive, NEVER loaded'),('inventory','inventory.json',b'{"testOnly":true}')]:
                (external/name).write_bytes(raw)
                m['external'][key]={'name':name,'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)}
            result=P['assemble'](m,reader,root/'out',external=external)
            self.assertTrue(result['buildable']);self.assertFalse(result['runtimeApproved'])
            recipe=(root/'out'/'Dockerfile').read_text()
            self.assertIn('FROM sha256:'+'b'*64,recipe);self.assertNotIn('RUN ',recipe)
            self.assertNotIn('COPY . ',recipe);self.assertIn('USER 65532:65532',recipe)
            (external/'extra').write_text('fabricated')
            with self.assertRaises(Blocked):P['assemble'](m,reader,root/'extra-output',external=external)
            self.assertFalse((root/'extra-output').exists())

    def test_default_blocks_product_and_unknown_external_before_writing(self):
        for mode in ('product','external'):
            m,reader=fixture()
            if mode=='product':m['blocked']=[{'code':'synthetic missing table'}]
            else:m['external']['status']='unverified'
            with tempfile.TemporaryDirectory() as root:
                target=Path(root)/'new'
                with self.assertRaises(Blocked):P['assemble'](m,reader,target)
                self.assertFalse(target.exists())

    def test_paths_hashes_duplicates_and_missing_source(self):
        for mode in ('absolute','escape','seed','main','duplicate','digest','blob','missing','unfixed'):
            m,reader=fixture()
            if mode in ('absolute','escape','seed','main'):
                m['files'][0]['path']={'absolute':'/tmp/file.py','escape':'tools/pilot_image_acceptance/../x.py',
                 'seed':'service/mcis_service/example_seed.py','main':'service/mcis_service/main.py'}[mode]
            if mode=='duplicate':m['files']*=2
            if mode=='digest':m['files'][0]['sha256']='0'*64
            if mode=='blob':m['files'][0]['blob']='0'*40
            if mode=='unfixed':m['commit']='HEAD'
            if mode=='missing':
                def reader(row):raise Blocked('synthetic missing object')
            with self.assertRaises(Blocked):P['snapshot'](m,reader)

    def test_symlink_parent_target_and_artifact_refused(self):
        m,reader=fixture()
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);plain=root/'plain';plain.mkdir();alias=root/'alias';alias.symlink_to(plain,target_is_directory=True)
            with self.assertRaises(Blocked):P['assemble'](m,reader,alias/'new',review_only=True)
            dangling=root/'out';dangling.symlink_to(root/'absent')
            with self.assertRaises(Blocked):P['assemble'](m,reader,dangling,review_only=True)
            (plain/'file').write_bytes(b'x');(plain/'link').symlink_to(plain/'file')
            with self.assertRaises(Blocked):P['verify_artifact'](plain,{'name':'link','sha256':hashlib.sha256(b'x').hexdigest(),'size':1})

    def test_git_reader_fixed_ref_and_file_modes_with_fake_git(self):
        from types import SimpleNamespace as NS
        m,reader=fixture();row=m['files'][0]
        for mode in ('ok','ref','promisor','link','missing'):
            calls=[]
            class FakeGit(P['GitObjects']):
                def command(self,args,check=True):
                    calls.append(args)
                    if args[0]=='config':return NS(returncode=0 if mode=='promisor' else 1,stdout=b'')
                    if args[0]=='rev-parse':return NS(stdout=(P['REF']+'\n').encode())
                    if mode=='missing':raise Blocked('missing fixed Git object')
                    if args[0]=='ls-tree':return NS(stdout=((('120000' if mode=='link' else '100644')+' blob '+row['blob']+'\t'+row['path']+'\n').encode()))
                    if args[:2]==['cat-file','-s']:return NS(stdout=str(row['size']).encode())
                    if args[:2]==['cat-file','blob']:return NS(stdout=reader(row))
                    raise AssertionError('unexpected Git command')
            with tempfile.TemporaryDirectory() as root:
                if mode=='ok':self.assertEqual(FakeGit(root,P['REF']).read(row),reader(row))
                else:
                    with self.assertRaises(Blocked):FakeGit(root,'HEAD' if mode=='ref' else P['REF']).read(row)
                if mode in ('link','promisor','ref'):
                    self.assertFalse(any(args[:2]==['cat-file','blob'] for args in calls))

    def test_real_frozen_manifest_metadata_only(self):
        root=ROOT/'tools/pilot_image_build';raw=(root/'inputs.json').read_bytes()
        self.assertEqual(P['digest'](raw),P['INPUTS_SHA'])
        self.assertEqual(P['digest']((root/'imports.json').read_bytes()),P['IMPORTS_SHA'])
        m=json.loads(raw);self.assertEqual(m['commit'],P['REF']);self.assertEqual(len(m['files']),57)
        self.assertEqual(m['blocked'][0]['code'],'MISSING_TRACK_RECEIPT_TABLE')
        self.assertIsNone(m['external']['base_image_id'])
        for row in m['files']:P['safe_path'](row['path'])
        evidence=json.loads((root/'imports.json').read_text())
        self.assertTrue(all(e.get('exclusion_basis') for e in evidence if e['omitted_local']))

if __name__=='__main__':unittest.main()
