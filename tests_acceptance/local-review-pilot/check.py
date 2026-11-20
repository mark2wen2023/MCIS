"""Standard library + extracted source with handmade request/app; no application import."""
import ast
import asyncio
from dataclasses import dataclass
from hashlib import sha256
import math
from pathlib import Path
import re
import runpy
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
import unittest

ROOT=Path(__file__).resolve().parents[2]
prior=runpy.run_path(str(ROOT/'tests_acceptance/verified-case-context/check.py'))
base=prior['scope'];Denied=prior['Denied'];Grant=prior['Grant']
source=(ROOT/'service/mcis_service/common/local_review_pilot.py').read_text();tree=ast.parse(source)
assert [n.module for n in tree.body if isinstance(n,ast.ImportFrom)]==['dataclasses','hashlib','urllib.parse','context','verified_case_context']
assert [n.names[0].name for n in tree.body if isinstance(n,ast.Import)]==['math','re','time']
scope={**base,'sha256':sha256,'math':math,'time':time,'urlsplit':urlsplit}
exec(compile(ast.Module(body=[n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))],type_ignores=[]),'<pilot source with fake adapters>','exec'),scope)
Session=scope['PilotSession'];Store=scope['PilotSessions'];install=scope['_install_local_review_pilot']
# Test-only fabricated strings; no issued session, real browser, service or bootstrap.
TOKEN='x'*43;DIGEST=sha256(TOKEN.encode()).hexdigest();ORIGIN='https://pilot.invalid'
class Headers:
    def __init__(self,values):self.values=values
    def getlist(self,key):return self.values.get(key,[])
def request(case='SYN-A',method='GET',path='/api/v1/cases/{case_id}/audio-reviews',changes=None):
    headers={'host':['pilot.invalid'],'sec-fetch-site':['same-origin'],'cookie':['__Host-MCIS-Pilot='+TOKEN]}
    if method!='GET':headers['origin']=[ORIGIN]
    headers.update(changes or {})
    return SimpleNamespace(scope={'scheme':'https','route':SimpleNamespace(path=path)},path_params={'case_id':case},headers=Headers(headers),method=method)
def setup(grants=None):
    clock=[10.0]
    grants=grants or frozenset({('SYN-A','audio.list'),('SYN-A','audio.revise'),('SYN-B','image.read')})
    store=Store({DIGEST:Session('pilot-subject','Investigator',20.0,grants)},clock=lambda:clock[0])
    app=SimpleNamespace(dependency_overrides={})
    dep=install(app,enabled=True,sessions=store,origin=ORIGIN)
    return store,clock,dep
class Checks(unittest.TestCase):
    def test_explicit_case_and_operation_verified_not_headers(self):
        _,_,dep=setup();ctx=asyncio.run(dep(request(changes={'x-mcis-role':['LeadInvestigator'],'x-mcis-operator':['client']})))
        self.assertEqual((ctx.role,ctx.operator),('Investigator','pilot-subject'))
        saved=asyncio.run(dep(request(method='POST',path='/api/v1/cases/{case_id}/audio-reviews/{run_id}/revisions')))
        self.assertEqual(saved.operator,'pilot-subject')
        second=asyncio.run(dep(request(case='SYN-B',path='/api/v1/cases/{case_id}/image-reviews/{run_id}')))
        self.assertEqual(second.operator,'pilot-subject')
        for req in [request(case='SYN-B'),request(method='POST'),request(case='REAL-A')]:
            with self.assertRaises(Denied):asyncio.run(dep(req))
    def test_expired_revoked_unknown_never_enters_fake_handler(self):
        for mode in ['expired','revoked','unknown']:
            store,clock,dep=setup();req=request();calls=[]
            if mode=='expired':clock[0]=20
            if mode=='revoked':store.revoke(DIGEST)
            if mode=='unknown':req=request(changes={'cookie':['__Host-MCIS-Pilot='+'y'*43]})
            async def dispatch():await dep(req);calls.append('handler')
            with self.assertRaises(Denied):asyncio.run(dispatch())
            self.assertEqual(calls,[])
    def test_cross_site_and_missing_origin_cookie_denied(self):
        _,_,dep=setup()
        for changes in [{'sec-fetch-site':['cross-site']},{'sec-fetch-site':[]},{'host':['other.invalid']},{'origin':['https://other.invalid']},{'origin':['null']},{'origin':[]},{'cookie':[]},{'cookie':['__Host-MCIS-Pilot='+TOKEN+'; __Host-MCIS-Pilot='+TOKEN]},{'authorization':['Bearer '+TOKEN]}]:
            with self.assertRaises(Denied):asyncio.run(dep(request(method='POST',path='/api/v1/cases/{case_id}/audio-reviews/{run_id}/revisions',changes=changes)))
        req=request();req.scope['scheme']='http'
        with self.assertRaises(Denied):asyncio.run(dep(req))
    def test_no_configuration_or_disabled_installs_denial(self):
        for kw in [{},{'enabled':True},{'enabled':False,'sessions':setup()[0],'origin':ORIGIN}]:
            app=SimpleNamespace(dependency_overrides={});dep=install(app,**kw)
            with self.assertRaises(Denied) as e:asyncio.run(dep(request()))
            self.assertEqual(e.exception.code,'IDENTITY_UNCONFIGURED')
    def test_strict_origin_and_session_configuration(self):
        for origin in ['http://pilot.invalid','https://pilot.invalid/','https://name:pass@pilot.invalid','https://pilot.invalid?q=1']:
            with self.assertRaises(ValueError):install(SimpleNamespace(dependency_overrides={}),enabled=True,sessions=setup()[0],origin=origin)
        for grant in [('REAL-A','audio.list'),('SYN-A','*'),('*','audio.list')]:
            with self.assertRaises(ValueError):Store({DIGEST:Session('s','Investigator',20,frozenset({grant}))})
        for expiry in [float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError):Store({DIGEST:Session('s','Investigator',expiry,frozenset())})
    def test_instances_and_cookie_policy_no_legacy_fallback(self):
        _,_,first=setup();empty=Store({},clock=lambda:10)
        second=install(SimpleNamespace(dependency_overrides={}),enabled=True,sessions=empty,origin=ORIGIN)
        self.assertEqual(asyncio.run(first(request())).operator,'pilot-subject')
        with self.assertRaises(Denied):asyncio.run(second(request()))
        self.assertEqual(scope['COOKIE_OPTIONS'],{'secure':True,'httponly':True,'samesite':'strict','path':'/'})
    def test_revocation_between_calls_and_bad_clock(self):
        store,clock,dep=setup();asyncio.run(dep(request()));store.revoke(DIGEST)
        with self.assertRaises(Denied):asyncio.run(dep(request()))
        _,clock,dep=setup();clock[0]=float('nan')
        with self.assertRaises(Denied):asyncio.run(dep(request()))
if __name__=='__main__':unittest.main()
