"""Factory AST + fake routes; original intake functions defined, NEVER invoked."""
import ast
import asyncio
from pathlib import Path
import runpy
import subprocess
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[2]
BASE='cb3f2fd895c3785cef611d522059ad263554d92d'
prior=runpy.run_path(str(ROOT/'tests_acceptance/pilot-factory/check.py'))
identity=prior['prior'];Denied=prior['Denied']
source=subprocess.check_output(['git','show',BASE+':service/mcis_service/evidence_intake/router.py'],cwd=ROOT,text=True)
tree=ast.parse(source)

class Checks(unittest.TestCase):
    def setup_factory(self,registration=False,grants=frozenset()):
        s=prior['setup']();sc=s.scope
        s.sessions=prior['Store']({identity['DIGEST']:prior['Session']('synthetic','Investigator',20.0,grants)},clock=lambda:10.0)
        class Router:
            def __init__(self,**kw):self.routes=[];self.route_class=kw['route_class']
            def add_api_route(self,path,fn,methods):self.routes.append(NS(path=path,methods=set(methods),endpoint=fn))
        def images(app):
            for method,path in sc['IMAGE_ROUTES']:
                if path.endswith('/evidence-intakes/{digest}') or path=='/pilot/image-review' or path.endswith('preview.js'):continue
                app.routes.append(NS(path=path,methods={method},endpoint=None))
        def pages(app):
            app.get('/pilot/image-review')(lambda:None)
            app.get('/image-review-lab/preview.js')(lambda:None)
        # Compile real handler bodies but never call them. Identity/Ctx defaults
        # evaluated against fake objects only; no transaction or body execution.
        endpoints={'Ctx':object,'CtxDep':object(),'Request':object}
        for name in ['preview_input','commit_input','receipt_input']:
            node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
            node=ast.parse(ast.unparse(node)).body[0];node.decorator_list=[]
            exec(compile(ast.Module(body=[node],type_ignores=[]),'<unexecuted real intake handlers>','exec'),endpoints)
        sc.update(APIRouter=Router,NoStoreRoute=object,_mount_image_imports_only=images,
                  _mount_pilot_image_pages=pages,_initialize_image_review_storage=lambda *a,**kw:None,
                  **{name:endpoints[name] for name in ['preview_input','commit_input','receipt_input']})
        app=s.construct(sessions=s.sessions,image_imports=True,image_blob_dir=sc['Path']('/synthetic'),evidence_registration=registration)
        return s,app,endpoints

    def test_explicit_switch_real_handlers_no_preparation_or_image_creation(self):
        for enabled in [False,True]:
            s,app,handlers=self.setup_factory(enabled)
            actual={(m,r.path) for r in app.routes for m in r.methods}
            expected=s.scope['ROUTES']|s.scope['IMAGE_ROUTES']|(s.scope['REGISTRATION_ROUTES'] if enabled else frozenset())
            self.assertEqual(actual,expected);self.assertEqual(len(actual),12 if enabled else 10)
            for suffix,name in [('preview','preview_input'),('commit','commit_input')]:
                routes=[r for r in app.routes if r.path.endswith('evidence-intakes:'+suffix)]
                self.assertEqual(len(routes),int(enabled))
                if enabled:self.assertIs(routes[0].endpoint,handlers[name])
            # Original handlers reference undefined runtime dependencies here;
            # construction success proves no handler/body was executed.
            self.assertFalse(any(isinstance(e,tuple) and e[0]=='read' for e in s.events))

    def test_invalid_configuration_before_any_construction(self):
        for opts in [dict(evidence_registration=True),dict(evidence_registration='true')]:
            s=prior['setup']()
            with self.assertRaises(ValueError):s.construct(**opts)
            self.assertEqual(s.events,[])

    def test_same_server_session_requires_each_case_operation(self):
        for operation,suffix in [('evidence.preview','preview'),('evidence.register','commit')]:
            s,app,_=self.setup_factory(True,frozenset({('SYN-A',operation)}))
            dependency=next(iter(app.dependency_overrides.values()))
            path='/api/v1/cases/{case_id}/evidence-intakes:'+suffix
            def request(case='SYN-A',path=path):
                r=identity['request'](case=case,method='POST',path=path,changes={'host':['127.0.0.1:8766'],'origin':['https://127.0.0.1:8766']});r.app=app;return r
            ctx=asyncio.run(dependency(request()));self.assertEqual(ctx.operator,'synthetic')
            with self.assertRaises(Denied):asyncio.run(dependency(request(case='SYN-B')))
            other='/api/v1/cases/{case_id}/evidence-intakes:'+('commit' if suffix=='preview' else 'preview')
            with self.assertRaises(Denied):asyncio.run(dependency(request(path=other)))
            s.sessions.revoke(identity['DIGEST'])
            with self.assertRaises(Denied):asyncio.run(dependency(request()))

    def test_preserved_real_handler_guard_order_static_only(self):
        node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='commit_input')
        text=ast.unparse(node)
        labels=['authorize(ctx, s, case_id, write=True)','await body_bounded(request)','inputs(body, commit=True)',
                'preview(body, raw, case_id, ctx.operator, ctx.role)','load_receipt(ctx, s, case_id, digest)',
                "contracts.validate('evidence-item', item)",'put_doc(s, EvidenceRow', 'evidence.append_custody(', 'exclusive_write(']
        positions=[text.index(label) for label in labels]
        self.assertEqual(positions,sorted(positions))
        self.assertIn('INTAKE_STALE',text);self.assertIn('INTAKE_CLEANUP_FAILED',text)
        self.assertNotIn('image_review',text)
        # Frozen intake source remains byte-for-byte unchanged in this candidate.
        current=subprocess.check_output(['git','show','HEAD:service/mcis_service/evidence_intake/router.py'],cwd=ROOT,text=True)
        self.assertEqual(current,source)

if __name__=='__main__':unittest.main()
