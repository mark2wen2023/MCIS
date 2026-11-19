"""Only new pure modules plus synthetic query/session doubles; no ORM/app import."""
import ast
import copy
from contextlib import nullcontext
from pathlib import Path
import runpy
from types import SimpleNamespace as NS
ROOT = Path(__file__).resolve().parents[2]
projector = runpy.run_path(str(ROOT/'service/mcis_service/reports/media_reference.py'))
source = ast.parse((ROOT/'service/mcis_service/reports/media_reference_reader.py').read_text())
# Resolve only its one local pure dependency explicitly, without package __init__.
source.body = [n for n in source.body if not (isinstance(n, ast.ImportFrom) and n.level)]
env = {k:projector[k] for k in ('ProjectionUnavailable','project_saved_media')}
exec(compile(source,'<pure reader>','exec'),env)
Reader=env['ScopedMediaReader']; read=env['read_exact_media_reference']; Error=env['ProjectionUnavailable']
# Extract fixture definition only, not the other script's tests.
ft=ast.parse((Path(__file__).with_name('check.py')).read_text())
fenv=dict(A='a'*64,B='b'*64,C='c'*64,D='d'*64)
exec(compile(ast.Module(body=[n for n in ft.body if isinstance(n,ast.FunctionDef) and n.name=='fixture'],type_ignores=[]),'<synthetic fixture>','exec'),fenv)
class Field:
    def __init__(self,name): self.name=name
    def __eq__(self,value): return (self.name,value)
class Model:
    case_id=Field('case_id');run_id=Field('run_id');revision=Field('revision')
class Query:
    def where(self,*conditions): self.conditions=conditions;return self
class Session:
    def __init__(self,rows): self.rows=rows;self.queries=[];self.no_autoflush=nullcontext()
    def scalars(self,q):
        self.queries.append(q.conditions)
        matches=[NS(**copy.deepcopy(r)) for r in self.rows if all(r[k]==v for k,v in q.conditions)]
        return NS(all=lambda:matches)
def setup(media):
    f=fenv['fixture'](media)
    h=f['saved_rows'][1]['doc'];h.update(reason='synthetic review reason',operator='synthetic operator',role='Investigator',utc='2026-01-01T00:00:00Z')
    if media=='audio':h.update(startMs=None,endMs=None,timeStatus='unknown',speaker={'status':'unknown','id':None})
    old=copy.deepcopy(f['saved_rows'][1]);old['revision']=2;old['doc'].update(revision=2,expectedRevision=1,text='later')
    other=copy.deepcopy(old);other['case_id']='OTHER'
    session=Session(f['saved_rows']+[old,other]);reads=[]
    def ev(case,eid):
        reads.append((case,eid))
        return next((copy.deepcopy(i) for i in f['evidence_items'] if i['caseId']==case and i['evidenceId']==eid),None)
    reader=Reader(case_id='CASE-SYN',session=session,select=lambda model:Query(),audio_model=Model,image_model=Model,evidence_reader=ev)
    args={k:f[k] for k in ('media','case_id','run_id','revision','evidence_id','evidence_role')}
    return f,session,reads,reader,args

def fail(args,reader,code):
    try:read(reader=reader,**args)
    except Error as e:assert e.code==code,(e.code,code)
    else:raise AssertionError(code)

for media in ('image','audio'):
    f,s,ev,r,a=setup(media); before=copy.deepcopy(s.rows); out=read(reader=r,**a)
    assert s.rows==before and out['projection']['humanText']!='later'
    assert s.queries==[(('case_id','CASE-SYN'),('run_id','RUN-SYN'),('revision',0)),(('case_id','CASE-SYN'),('run_id','RUN-SYN'),('revision',1))]
    assert ev==([('CASE-SYN','EV-A'),('CASE-SYN','EV-B')] if media=='image' else [('CASE-SYN','EV-A')])
    digest=out['referenceSha256']; humanhash=out['projection']['humanRevisionSha256']
    assert read(reader=r,expected_reference_sha256=digest,**a)==out
    # Dict insertion order is immaterial; saved text at same exact keys is not.
    s.rows[1]['doc']=dict(reversed(list(s.rows[1]['doc'].items())))
    assert read(reader=r,**a)==out
    s.rows[1]['doc']['text']='changed at same revision'
    changed=read(reader=r,**a)
    assert changed['projection']['humanRevisionSha256']!=humanhash and changed['referenceSha256']!=digest
    fail(dict(a,expected_reference_sha256=digest),r,'reference_content_changed')
    f,s,ev,r,a=setup(media);a['revision']=3;fail(a,r,'revision_missing');assert not ev
    assert [q[-1][1] for q in s.queries]==[0,3] # no latest/list/history query
    f,s,ev,r,a=setup(media);a['case_id']='OTHER';fail(a,r,'case_mismatch');assert not s.queries and not ev
    f,s,ev,r,a=setup(media)
    class WrongRow:
        case_id='CASE-SYN'
        def read_revision(self,*args):return [dict(f['saved_rows'][0],case_id='OTHER')]
        def read_evidence(self,*args):raise AssertionError('must not read evidence')
    fail(a,WrongRow(),'case_mismatch')
    f,s,ev,r,a=setup(media);s.rows[1]['doc'].pop('reason');fail(a,r,'revision_content_unknown')
    print('PASS',media,'exact query/digest/missing/cross-case/unrelated-row/no-write method checks')
print('COMPLETE: handcrafted query semantics, not SQLAlchemy/HTTP/permissions/storage acceptance')
