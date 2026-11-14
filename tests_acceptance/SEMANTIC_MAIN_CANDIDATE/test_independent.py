"""Independent minimal extraction proof: seven files, stdlib-only isolated CLI."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'research/semantic_support'
RUNTIME=['evaluate.py','render_review.py','export_review.py','render_browser_review.py','render_restore_review.py','browser_review.js','browser_import.js']
WRAPPER="""import socket,sys,runpy
from pathlib import Path
def denied(*a,**k): raise AssertionError('network forbidden')
socket.socket=denied;socket.create_connection=denied
entry=sys.argv[1];sys.path.insert(0,str(Path(entry).parent));sys.argv=sys.argv[1:]
runpy.run_path(entry,run_name='__main__')
"""


@pytest.fixture
def isolated(tmp_path):
    runtime=tmp_path/'runtime';runtime.mkdir()
    for name in RUNTIME:shutil.copyfile(SOURCE/name,runtime/name)
    inputs=tmp_path/'inputs';inputs.mkdir()
    for name in ['jiangxin9-provisional.json','jiangxin9-real-predictions.json']:
        shutil.copyfile(SOURCE/name,inputs/name)
    return runtime,inputs,tmp_path


def run(files,entry,*args):
    runtime,inputs,tmp=files
    command=[sys.executable,'-I','-S','-B','-c',WRAPPER,str(runtime/entry),*map(str,args)]
    return subprocess.run(command,cwd=tmp,capture_output=True,text=True,timeout=15)


def input_args(files):
    return ['--corpus',files[1]/'jiangxin9-provisional.json','--predictions',files[1]/'jiangxin9-real-predictions.json']


def test_manifest_all40_files_match_original_git_bytes():
    manifest=json.loads((Path(__file__).parent/'source-manifest.json').read_text())
    assert len(manifest)==40 and len({row['path'] for row in manifest})==40
    for row in manifest:
        original=subprocess.run(['git','show',row['sourceCommit']+':'+row['path']],cwd=ROOT,capture_output=True,check=True).stdout
        actual=(ROOT/row['path']).read_bytes()
        assert original==actual and hashlib.sha256(actual).hexdigest()==row['sha256']
    assert sorted(Path(row['path']).name for row in manifest if Path(row['path']).name in RUNTIME)==sorted(RUNTIME)


def test_main_ancestry_and42_frozen_files():
    base='3aba2bf03e393909c611489ae573a887087637ac'
    actual=subprocess.run(['git','merge-base',base,'HEAD'],cwd=ROOT,capture_output=True,text=True,check=True)
    assert actual.stdout.strip()==base
    assert subprocess.run(['git','merge-base','--is-ancestor','254167e3e957784fd9d2d136a275731f33314d9b','HEAD'],cwd=ROOT).returncode==1
    lines=(ROOT/'logs/semantic-main-candidate-impl-hashes-frozen.txt').read_text().splitlines()
    assert len(lines)==42
    for line in lines:
        digest,path=line.split(maxsplit=1)
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest


def test_runtime_import_graph_has_only_stdlib_and_selected_modules():
    modules={Path(name).stem for name in RUNTIME if name.endswith('.py')}
    for name in RUNTIME:
        if not name.endswith('.py'):continue
        for node in ast.walk(ast.parse((SOURCE/name).read_bytes())):
            if isinstance(node,ast.Import):names=[item.name for item in node.names]
            elif isinstance(node,ast.ImportFrom):names=[node.module]
            else:continue
            assert all(item.split('.')[0] in sys.stdlib_module_names|modules for item in names)


def test_seven_file_cli_to_actual_js_download_restore_and_html_export(isolated):
    runtime,_,tmp=isolated;page=tmp/'page.html';worksheet=tmp/'notes.json';snapshot=tmp/'snapshot.html'
    result=run(isolated,'render_restore_review.py',*input_args(isolated),'--output',page)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['modelCalled'] is False
    assert sorted(p.name for p in runtime.iterdir())==sorted(RUNTIME)
    # Execute actual embedded export and import scripts through the existing adapters.
    for script,extra in [('browser-review.test.cjs',[worksheet]),('browser-import.test.cjs',[])]:
        result=subprocess.run(['node',str(SOURCE/script),str(page),*map(str,extra)],cwd=tmp,capture_output=True,text=True,timeout=15)
        assert result.returncode==0,result.stdout+result.stderr
    notes=json.loads(worksheet.read_text());assert notes['status']=='unverified_research_notes_not_case_facts'
    result=run(isolated,'export_review.py','export',*input_args(isolated),'--worksheet',worksheet,'--output',snapshot)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)=={'ok':True,'fileWritten':True,'caseUpdated':False,'reviewerAuthenticated':False,'modelCalled':False}
    html=snapshot.read_text()
    assert '未标记（不表示核实通过）' in html and '不是案件事实' in html
    assert notes['corpusSha256'] in html and notes['predictionsSha256'] in html
    assert '<script>alert(1)</script>' not in html


@pytest.mark.parametrize('field',['corpusSha256','predictionsSha256'])
def test_wrong_digest_rejected_without_output_in_isolation(isolated,field):
    worksheet=isolated[2]/'notes.json';output=isolated[2]/'no-output.html'
    assert run(isolated,'export_review.py','template',*input_args(isolated),'--output',worksheet).returncode==0
    notes=json.loads(worksheet.read_text());notes[field]='0'*64;worksheet.write_text(json.dumps(notes))
    result=run(isolated,'export_review.py','export',*input_args(isolated),'--worksheet',worksheet,'--output',output)
    assert result.returncode==2 and not output.exists()
    assert json.loads(result.stderr)['errorCode']=='RESEARCH_NOTES_EXPORT_REJECTED'


def test_output_exclusivity_and_symlink_refusal(isolated):
    output=isolated[2]/'page.html'
    args=[*input_args(isolated),'--output',output]
    assert run(isolated,'render_restore_review.py',*args).returncode==0
    content=output.read_bytes()
    assert os.stat(output).st_mode&0o777==0o600
    assert run(isolated,'render_restore_review.py',*args).returncode==2
    assert output.read_bytes()==content
    link=isolated[2]/'symlink.html';link.symlink_to(output)
    assert run(isolated,'render_restore_review.py',*input_args(isolated),'--output',link).returncode==2
    assert output.read_bytes()==content


def test_evaluation_never_upgrades_source_model_or_fact_status(isolated):
    result=run(isolated,'evaluate.py',*input_args(isolated));assert result.returncode==0,result.stderr
    data=json.loads(result.stdout)
    for field in ['realModelCalled','factActivated','semanticSupportVerified','expertCertificationVerified']:
        assert data[field] is False
    for item in data['items']:
        assert item['sourceLocatorVerified'] is False and item['verifiedHumanReviewers']==0
        assert item['prediction']['modelIdentityVerified'] is False
        assert item['prediction']['provenanceVerified'] is False
        assert item['prediction']['status']=='external_proposed_unreviewed'
