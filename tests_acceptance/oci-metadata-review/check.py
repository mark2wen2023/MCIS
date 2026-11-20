"""Only newly fabricated tiny archives; no Docker, app or real image input."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
TOOL=ROOT/'tools/oci_metadata_review/check.py'
P=runpy.run_path(str(TOOL))
sha=lambda b:hashlib.sha256(b).hexdigest()
def js(v):return json.dumps(v,separators=(',',':')).encode()
def fixture(platform=None, config_change=None, index_change=None, manifest_change=None):
    platform=platform or {'os':'linux','architecture':'amd64'}
    layer=gzip.compress(bytes(1024),mtime=0)
    config=dict(platform, rootfs={'type':'layers','diff_ids':['sha256:'+sha(bytes(1024))]})
    if config_change:config_change(config)
    config=js(config)
    def desc(raw,typ):return {'mediaType':typ,'digest':'sha256:'+sha(raw),'size':len(raw)}
    manifest={'schemaVersion':2,'mediaType':P['MANIFEST'],'config':desc(config,P['CONFIG']),'layers':[desc(layer,P['LAYER'])]}
    if manifest_change:manifest_change(manifest)
    manifest=js(manifest)
    index={'schemaVersion':2,'manifests':[dict(desc(manifest,P['MANIFEST']),platform=platform)]}
    if index_change:index_change(index)
    return [('oci-layout',js({'imageLayoutVersion':'1.0.0'})),('index.json',js(index))]+[
        ('blobs/sha256/'+sha(b),b) for b in [manifest,config,layer]]
def archive(rows,typ=None):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        for i,(name,raw) in enumerate(rows):
            info=tarfile.TarInfo(name);info.size=len(raw)
            if typ and i==0:info.type=typ; info.size=0;info.linkname='forbidden'
            tar.addfile(info,io.BytesIO(raw))
    return out.getvalue()

class Checks(unittest.TestCase):
    def run_bytes(self,raw,**kwargs):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.tar';p.write_bytes(raw)
            return P['review'](p,kwargs.pop('expected_sha',sha(raw)),kwargs.pop('expected_size',len(raw)),**kwargs)
    def reject(self,raw,code=None,**kwargs):
        with self.assertRaises(P['Rejected']) as c:self.run_bytes(raw,**kwargs)
        if code:self.assertEqual(str(c.exception),code)
    def test_normal_and_explicit_platform(self):
        for target,platform in [('linux/amd64',None),('linux/arm64/v8',{'os':'linux','architecture':'arm64','variant':'v8'})]:
            result=self.run_bytes(archive(fixture(platform)),platform=target)
            self.assertEqual(result['result'],'metadata_checked');self.assertEqual(result['members'],5)
            self.assertEqual(result['layers'],1)
            for k in ('runtimeApproved','inventoryVerified','rootfsDiffIdsVerified','dependencyAbiVerified','provenanceVerified','builderVerified'):self.assertIs(result[k],False)
    def test_platform_and_ambiguity(self):
        self.reject(archive(fixture()),'PLATFORM_MISMATCH',platform='linux/arm64/v8')
        self.reject(archive(fixture(config_change=lambda c:c.update(architecture='arm64'))),'CONFIG_PLATFORM')
        self.reject(archive(fixture(index_change=lambda i:i['manifests'].append(i['manifests'][0]))),'AMBIGUOUS_PLATFORM')
        self.reject(archive(fixture()),'UNSUPPORTED_PLATFORM',platform='arbitrary-private-text')
    def test_archive_digest_size_and_blob_corruption(self):
        rows=fixture();raw=archive(rows)
        self.reject(raw,'ARCHIVE_HASH',expected_sha='0'*64)
        self.reject(raw,'ARCHIVE_SIZE',expected_size=len(raw)+512)
        rows[-1]=(rows[-1][0],b'x'+rows[-1][1][1:]);self.reject(archive(rows),'BLOB_HASH')
        self.reject(archive(fixture(manifest_change=lambda m:m['layers'][0].update(size=1))),'DESCRIPTOR_MISMATCH')
    def test_dangerous_and_duplicate_members(self):
        rows=fixture()
        for name in ('../escape','/absolute','blobs/../index.json','./index.json','manifest.json'):
            self.reject(archive(rows+[(name,b'{}')]),'MEMBER_PATH')
        self.reject(archive(rows+[rows[0]]),'MEMBER_DUPLICATE')
        for kind in (tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.DIRTYPE,tarfile.FIFOTYPE,tarfile.XHDTYPE):
            self.reject(archive(rows,kind),'MEMBER_TYPE')
    def test_unsupported_and_unreferenced(self):
        self.reject(gzip.compress(archive(fixture())).ljust(1024,b'\0'))
        self.reject(archive([('manifest.json',b'[]')]),'MEMBER_PATH')
        self.reject(archive(fixture()+[('blobs/sha256/'+sha(b'extra'),b'extra')]),'UNREFERENCED_MEMBER')
        self.reject(archive(fixture(manifest_change=lambda m:m['layers'][0].update(mediaType='application/vnd.oci.image.layer.v1.tar'))),'UNSUPPORTED_MEDIA_TYPE')
        self.reject(archive(fixture()[:-1]),'MEMBER_MISSING')
    def test_json_and_limits(self):
        rows=fixture();rows[1]=('index.json',b'{"schemaVersion":2,"schemaVersion":2}')
        self.reject(archive(rows),'JSON_DUPLICATE')
        rows[1]=('index.json',b'[]');self.reject(archive(rows),'UNSUPPORTED_METADATA')
        rows[1]=('index.json',b' '* (P['MAX_METADATA']+1));self.reject(archive(rows),'METADATA_LIMIT')
        self.reject(archive(fixture()),'ARCHIVE_LIMIT',expected_size=P['MAX_ARCHIVE']+512)
        # Hand-written lowered bound exercises member limit without huge fixture.
        scope=P['scan'].__globals__;old=scope['MAX_MEMBERS'];scope['MAX_MEMBERS']=4
        try:self.reject(archive(fixture()),'MEMBER_LIMIT')
        finally:scope['MAX_MEMBERS']=old
    def test_headers_padding_and_trailing(self):
        raw=bytearray(archive(fixture()));raw[0]^=1;self.reject(bytes(raw),'TAR_CHECKSUM')
        raw=bytearray(archive(fixture()));raw[512+len(fixture()[0][1])]=1;self.reject(bytes(raw),'TAR_PADDING')
        self.reject(archive(fixture())+b'x'*512,'TAR_TRAILING')
        self.reject(archive(fixture())[:1024])
    def test_descriptor_bound_and_no_path_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'PRIVATE_PATH';raw=archive(fixture());p.write_bytes(raw)
            link=Path(d)/'link';link.symlink_to(p)
            with self.assertRaises(OSError):P['review'](link,sha(raw),len(raw))
            hard=Path(d)/'hard';os.link(p,hard)
            with self.assertRaises(P['Rejected']):P['review'](p,sha(raw),len(raw))
            hard.unlink()
            cmd=[sys.executable,'-I',str(TOOL),'--archive',str(p),'--size',str(len(raw)),'--sha256',sha(raw)]
            r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0)
            self.assertEqual(len(r.stdout.splitlines()),1);self.assertNotIn(str(p),r.stdout+r.stderr)
            r=subprocess.run(cmd+['--unknown-private-secret'],capture_output=True,text=True)
            self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['code'],'ARGUMENTS')
            self.assertNotIn('secret',r.stdout+r.stderr);self.assertFalse(r.stderr)
    def test_changed_descriptor_detected(self):
        # No concurrent file manipulation: fstat observation substitute only.
        from types import SimpleNamespace
        real=os.fstat;calls=[]
        def changed(fd):
            s=real(fd);calls.append(1)
            return SimpleNamespace(**{k:getattr(s,k)+(1 if k=='st_mtime_ns' and len(calls)>1 else 0)
                for k in ('st_mode','st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_nlink')})
        os.fstat=changed
        try:self.reject(archive(fixture()),'INPUT_CHANGED')
        finally:os.fstat=real

if __name__=='__main__':unittest.main()
