"""将三船的完整输出按冻结官方 Schema、正式校验入口及原始 CAD 句柄逐一核验。"""
import argparse,hashlib,json,subprocess,sys,tarfile,tempfile
from pathlib import Path
import ezdxf
from jsonschema import Draft202012Validator
P=Path(__file__).resolve().parent
def leaves(o):
    if isinstance(o,dict):
        if 'source_sha256' in o and 'instance' in o:yield o['source_sha256'],o['instance']
        for v in o.values():yield from leaves(v)
    elif isinstance(o,list):
        for v in o:yield from leaves(v)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('repo',type=Path);parser.add_argument('run')
    a=parser.parse_args();run=P/'runs'/a.run;rev=json.loads((run/'summary.json').read_bytes())['commit'];rows=[]
    with tempfile.TemporaryDirectory() as d,tempfile.TemporaryFile() as f:
        subprocess.run(['git','-C',str(a.repo),'archive',rev,'ship-reconstruction'],stdout=f,check=True);f.seek(0)
        with tarfile.open(fileobj=f) as t:t.extractall(d,filter='data')
        base=Path(d)/'ship-reconstruction';schema=json.loads((base/'schemas/geometry.schema.json').read_bytes())
        validator=Draft202012Validator(schema)
        for case in 'ABC':
            path=run/case/'out/geometry.json';g=json.loads(path.read_bytes());out=Path(d)/case
            exitcode=subprocess.run([sys.executable,str(base/'scripts/s2.py'),'geometry_data_validate',str(path),'--out',str(out)],capture_output=True).returncode
            cli=json.loads((out/'geometry_data_validate.json').read_bytes())
            docs={hashlib.sha256(x.read_bytes()).hexdigest():ezdxf.readfile(x) for x in (P/'casebook/inputs'/case).glob('*.dxf')}
            bad=[];ev=0
            for k in ['modeling_admission','topology_features','uncertainties','conflicts','coordinate_system']:
                for sha,inst in leaves(g[k]):
                    ev+=1;doc=docs.get(sha);hs=inst.split('/')
                    if doc is None or any(h not in doc.entitydb for h in hs):bad.append([sha,inst]);continue
                    for i,h in enumerate(hs[:-1]):
                        ins=doc.entitydb[h];child=doc.entitydb[hs[i+1]]
                        if ins.dxftype()!='INSERT' or child.dxf.owner!=doc.blocks[ins.dxf.name].block_record_handle:bad.append([sha,inst])
            errors=[v.message for v in validator.iter_errors(g)];state=g['modeling_admission']['state']
            conflict_expected=case=='B';cf=g['conflicts'];state_ok=state=='blocked' and not g['modeling_admission']['allowed_regions'] and not g['modeling_admission']['engineering_approved']
            col=[r for r in cf if r['kind']=='cell_conflict' or 'offset' in r['kind'] or 'conflict' in r['kind']]
            conflict_ok=(len(cf)==1 and len(cf[0].get('evidence',[]))==2) if conflict_expected else len(cf)==0
            rows.append(dict(case=case,commit=rev,version=g['schema_version'],json_schema_errors=errors,formal_cli_exit=exitcode,formal_cli=cli,admission=state,correct_research_scope=state_ok,expected_conflict=conflict_expected,reported_conflicts=len(cf),correct_conflict_count=conflict_ok,evidence_checked=ev,bad_evidence=bad,topology_features=len(g['topology_features']),all_pass=not errors and exitcode==0 and cli['valid'] and state_ok and conflict_ok and not bad))
    (run/'S2.1契约交接核验.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print([(r['case'],r['all_pass'],len(r['json_schema_errors']),r['evidence_checked']) for r in rows])
if __name__=='__main__':main()
