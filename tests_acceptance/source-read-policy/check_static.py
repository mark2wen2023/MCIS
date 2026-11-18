"""AST-only inspection of specified code files; never imports application or seeds."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'service/mcis_service'
files=['config.py','main.py','analysis/router.py','reports/service.py','reports/sources.py','common/source_policy.py']
trees={f:ast.parse((root/f).read_text(),filename=f) for f in files}
def function(file,name):return next(n for n in ast.walk(trees[file]) if isinstance(n,ast.FunctionDef) and n.name==name)
load=function('analysis/router.py','load_seed')
assert len(load.body)==1 and isinstance(load.body[0],ast.Return)
call=load.body[0].value
assert isinstance(call,ast.Call) and call.func.id=='read_analysis' and call.args[1].id=='_read_seed'
for name in ['list_analysis_cases','get_analysis']:
    f=function('analysis/router.py',name)
    assert isinstance(f.body[0],ast.Assign) and f.body[0].value.func.id=='_request_seed'
settings=next(n for n in trees['config.py'].body if isinstance(n,ast.ClassDef) and n.name=='Settings')
for name in ['allow_analysis_seed_reads','allow_public_report_reads']:
    field=next(n for n in settings.body if isinstance(n,ast.AnnAssign) and n.target.id==name)
    assert isinstance(field.value,ast.Constant) and field.value.value is False
main=function('main.py','create_app')
assert any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='source_read_policy' for t in n.targets) for n in main.body)
report=function('reports/service.py','create_report')
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='build_sections' and any(k.arg=='source_policy' for k in n.keywords) for n in ast.walk(report))
sources=trees['reports/sources.py']
assert not any(isinstance(n,ast.ImportFrom) and any(a.name=='public_text' for a in n.names) for n in sources.body)
f=function('reports/sources.py','build_sections')
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='read_public_report' for n in ast.walk(f))
print('PASS specified AST wiring checks; not runtime/API/complete import-closure validation')
