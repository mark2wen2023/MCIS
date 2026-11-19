"""Only AST-extracted functions with handmade dependencies; no actual app/ORM."""
import ast
from copy import deepcopy
from pathlib import Path
import subprocess
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
BASE='df05eb6b0cbbc0494ea44a05d3d4bbfbb356b7f3'


def old_source(path):
    return subprocess.run(['/usr/bin/git','-C',str(ROOT),'show',BASE+':'+path],
        env={'PATH':'/usr/bin:/bin','GIT_NO_LAZY_FETCH':'1','GIT_CONFIG_NOSYSTEM':'1',
             'GIT_CONFIG_GLOBAL':'/dev/null'},check=True,capture_output=True).stdout.decode()


def exercise(tree, media, mode):
    register='register_'+media+'_review'
    helpers=('_initialize_'+media+'_review_storage','_mount_'+media+'_review_routes')
    functions=[deepcopy(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in (register,*helpers)]
    events=[]
    runtime=object()
    failure=RuntimeError('synthetic initialization stop')
    flag=media+'_review_registered'
    runtime_field='image_ocr_runtime' if media=='image' else 'audio_asr_runtime'
    class State:
        def __setattr__(self,name,value):
            if name in (runtime_field,flag):
                events.append(('state',name,'runtime' if value is runtime else value))
            object.__setattr__(self,name,value)
    class Context:
        def __enter__(self):events.append(('enter',));return self
        def execute(self,value):events.append(('execute',value))
        def __exit__(self,*args):events.append(('exit',));return False
    def begin():events.append(('begin',));return Context()
    engine=SimpleNamespace(begin=begin)
    def create_all(received):
        assert received is engine
        events.append(('create_all',))
        if mode=='early-failure':raise failure
    def include_router(value):events.append(('include',value))
    response=object()
    def get(path,**kwargs):
        events.append(('get',path,kwargs.get('response_class') is response))
        def decorator(fn):
            events.append(('decorate',fn.__name__))
            # Never invoke the page/preview body or read its HTML/JS files.
            return fn
        return decorator
    state=State();state.db=SimpleNamespace(engine=engine)
    if mode=='duplicate':setattr(state,flag,True)
    events.clear()
    app=SimpleNamespace(state=state,include_router=include_router,get=get)
    def importer(name,globals=None,locals=None,fromlist=(),level=0):
        assert level==1
        if media=='image':
            assert name=='tasks' and fromlist==('router',)
            value=SimpleNamespace(router='tasks-router')
        else:
            assert name=='' and fromlist==('tasks',)
            value=SimpleNamespace(tasks=SimpleNamespace(router='tasks-router'))
        events.append(('import',name,fromlist))
        return value
    env={'__builtins__':{'getattr':getattr,'ValueError':ValueError,'__import__':importer},
         'Storage':SimpleNamespace(metadata=SimpleNamespace(create_all=create_all)),
         'sql':lambda value:value,'router':'review-router','HTMLResponse':response}
    exec(compile(ast.Module(body=functions,type_ignores=[]),'<extracted register with fakes>','exec'),env)
    try:
        result=env[register](app,**{('ocr_runtime' if media=='image' else 'sensevoice_runtime'):runtime})
    except Exception as error:
        if mode=='early-failure':assert error is failure
        elif mode=='duplicate':assert type(error) is ValueError and str(error)==media+' review already registered'
        else:raise
        outcome=mode
    else:
        assert mode=='normal' and result is app
        outcome='normal'
    if mode=='duplicate':assert events==[]
    elif mode=='early-failure':
        assert [event[0] for event in events]==['import','state','create_all']
        assert not getattr(state,flag,False)
    else:
        assert getattr(state,flag) is True
        assert getattr(state,runtime_field) is runtime
        assert [event[1] for event in events if event[0]=='include']==['review-router','tasks-router']
        assert len([event for event in events if event[0]=='execute'])==2
        assert events[-1]==('state',flag,True)
    return events,outcome


for media in ('image','audio'):
    path=f'service/mcis_service/{media}_review/app.py'
    old_text=old_source(path);new_text=(ROOT/path).read_text()
    old,new=ast.parse(old_text),ast.parse(new_text)
    names=('_initialize_'+media+'_review_storage','_mount_'+media+'_review_routes')
    helpers={n.name:n for n in new.body if isinstance(n,ast.FunctionDef) and n.name in names}
    assert set(helpers)==set(names)
    expanded=deepcopy(new)
    expanded.body=[n for n in expanded.body if not(isinstance(n,ast.FunctionDef) and n.name in names)]
    register=next(n for n in expanded.body if isinstance(n,ast.FunctionDef) and n.name=='register_'+media+'_review')
    body=[]
    for node in register.body:
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id in helpers:
            helper=helpers[node.value.func.id]
            assert not node.value.keywords
            assert [ast.unparse(a) for a in node.value.args]==[a.arg for a in helper.args.args]
            body.extend(deepcopy(helper.body))
        else:body.append(node)
    register.body=body
    assert ast.dump(expanded)==ast.dump(old), 'only the two helper boundaries may differ'
    # Trigger source expression, including f-string punctuation/spacing, is verbatim.
    sql_segments=lambda text,tree:[ast.get_source_segment(text,n) for n in ast.walk(tree)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='sql']
    assert sql_segments(old_text,old)==sql_segments(new_text,new)
    for mode in ('normal','duplicate','early-failure'):
        assert exercise(old,media,mode)==exercise(new,media,mode)
        print('PASS old/new synthetic sequence:',media,mode)
print('PASS complete AST expansion and verbatim SQL expressions; no real imports/DDL/pages executed')
