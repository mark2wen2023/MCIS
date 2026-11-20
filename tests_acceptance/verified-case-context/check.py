"""Only AST and hand-written request/handler substitutes; no FastAPI/app/ORM import."""
import ast
import asyncio
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[2]
class Denied(Exception):
    def __init__(self,status,code,message):self.status=status;self.code=code
@dataclass
class Context:
    role:str
    operator:str
    request:object

def legacy():pass
source=(ROOT/'service/mcis_service/common/verified_case_context.py').read_text()
tree=ast.parse(source)
# Execute only the candidate definitions with explicit handwritten dependencies.
assert [n.module for n in tree.body if isinstance(n,ast.ImportFrom)]==['dataclasses','fastapi','context']
assert [n.names[0].name for n in tree.body if isinstance(n,ast.Import)]==['re']
ctx_tree=ast.parse(subprocess.check_output(['git','show','33e0ceb:service/mcis_service/common/context.py'],cwd=ROOT,text=True))
roles=ast.literal_eval(next(n.value for n in ctx_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROLES' for t in n.targets)))
scope={'dataclass':dataclass,'re':re,'Request':object,'Ctx':Context,'ROLES':roles,'get_ctx':legacy,'problem':Denied}
exec(compile(ast.Module(body=[n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))],type_ignores=[]),'<candidate AST fake dependencies>','exec'),scope)
Grant=scope['CaseGrant'];make=scope['_make_verified_case_dependency'];install=scope['_install_verified_case_context']
class Headers:
    def __init__(self,values):self.values=values
    def getlist(self,key):
        assert key=='authorization'  # No role/operator headers trusted.
        return self.values

def request(case='SYN-A',method='GET',path='/api/v1/cases/{case_id}/audio-reviews',values=None):
    return SimpleNamespace(scope={'route':SimpleNamespace(path=path)},path_params={'case_id':case},method=method,headers=Headers(['Bearer fabricated-noncredential'] if values is None else values))

class Checks(unittest.TestCase):
    def test_no_verifier_or_missing_credential_never_reaches_handler(self):
        calls=[]
        async def verifier(*args):calls.append('verify');return None
        async def dispatch(dep,req):
            ctx=await dep(req);calls.append('handler');return ctx
        for dep,req in [(make(),request())]+[(make(verifier),request(values=v)) for v in [[],[''],['Bearer '],['Bearer x','Bearer y'],['Basic fake'],['Bearer x y']]]:
            with self.assertRaises(Denied):asyncio.run(dispatch(dep,req))
        self.assertEqual(calls,[])
    def test_all_mapped_operations_scope_then_verified_identity_then_handler(self):
        for (method,path),op in scope['_OPERATIONS'].items():
            calls=[]
            async def verifier(credential,case,operation):
                calls.append(('verify',case,operation));return Grant('synthetic-subject','Investigator',case,operation)
            async def dispatch():
                ctx=await make(verifier)(request(method=method,path=path));calls.append(('handler',ctx.operator,ctx.role));return ctx
            result=asyncio.run(dispatch())
            self.assertEqual(calls,[('verify','SYN-A',op),('handler','synthetic-subject','Investigator')]);self.assertEqual(result.request.path_params['case_id'],'SYN-A')
    def test_grant_mismatch_failure_or_provider_error_has_no_handler(self):
        for output in [None,Grant('s','Investigator','SYN-B','audio.list'),Grant('s','Investigator','SYN-A','audio.revise'),Grant('s','Unknown','SYN-A','audio.list'),Grant('','Investigator','SYN-A','audio.list'),{'subject':'client-state'},RuntimeError('synthetic secret not echoed')]:
            calls=[]
            async def verifier(*args):
                calls.append('verify')
                if isinstance(output,Exception):raise output
                return output
            async def dispatch():await make(verifier)(request());calls.append('handler')
            with self.assertRaises(Denied) as error:asyncio.run(dispatch())
            self.assertEqual(calls,['verify']);self.assertNotIn('synthetic secret',str(error.exception))
    def test_unknown_routes_and_cases_block_before_verifier(self):
        async def verifier(*args):raise AssertionError('must not call')
        for req in [request(case=''),request(case=' A'),request(path='/api/v1/cases'),request(path='/api/v1/cases/{case_id}/overview'),request(path='/api/v1/cases/{case_id}/audio-tasks'),request(method='DELETE')]:
            with self.assertRaises(Denied) as e:asyncio.run(make(verifier)(req))
            self.assertEqual(e.exception.code,'CASE_SCOPE_REQUIRED')
    def test_per_app_installation_no_default_mutation(self):
        a=SimpleNamespace(dependency_overrides={});b=SimpleNamespace(dependency_overrides={})
        async def verifier(token,case,op):return Grant('s','Investigator',case,op)
        dep=install(a,verifier=verifier);other=install(b)
        self.assertIs(a.dependency_overrides[legacy],dep);self.assertIsNot(dep,other)
        with self.assertRaises(ValueError):install(a)
        self.assertEqual(asyncio.run(dep(request())).operator,'s')
        with self.assertRaises(Denied):asyncio.run(other(request()))
    def test_route_templates_and_ctx_dependencies_are_real(self):
        found={}
        for path,prefix in [('cases/basic_registration.py','/api/v1'),('evidence_intake/router.py','/api/v1/cases/{case_id}'),('image_review/app.py','/api/v1/cases/{case_id}/image-reviews'),('audio_review/app.py','/api/v1/cases/{case_id}/audio-reviews')]:
            data=subprocess.check_output(['git','show','33e0ceb:service/mcis_service/'+path],cwd=ROOT,text=True)
            parsed=ast.parse(data)
            for fn in ast.walk(parsed):
                if not isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
                for d in fn.decorator_list:
                    if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and isinstance(d.func.value,ast.Name) and d.func.value.id=='router' and d.args and isinstance(d.args[0],ast.Constant):
                        key=(d.func.attr.upper(),prefix+d.args[0].value)
                        found[key]=any(isinstance(n,ast.Name) and n.id=='CtxDep' for n in fn.args.defaults)
        for key in scope['_OPERATIONS']:self.assertTrue(found.get(key),key)
        # Old context remains unchanged; candidate is not installed in an entrypoint.
        self.assertEqual(subprocess.check_output(['git','diff','33e0ceb','--','service/mcis_service/common/context.py','service/mcis_service/main.py','service/mcis_service/media_review_demo.py'],cwd=ROOT),b'')

if __name__=='__main__':unittest.main()
