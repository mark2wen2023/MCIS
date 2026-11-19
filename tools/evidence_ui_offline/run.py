"""Frozen representative front-end checks across two explicit checkouts; no app startup."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent

def fail(message):
    raise ValueError(message)

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE).strip()

def verify(root, spec):
    if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
        fail('必须传入检出根目录: '+str(root))
    base = spec['baseline']
    if git(root, 'cat-file', '-t', base) != 'commit':
        fail('固定基线对象缺失；本脚本不会 fetch')
    if subprocess.run(['git','-C',str(root),'merge-base','--is-ancestor',base,'HEAD'], capture_output=True).returncode:
        fail('HEAD 不包含固定基线（浅克隆也须有可证祖先链）: '+str(root))
    for name, digest in spec['files'].items():
        p = root/name
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root):
            fail('受测源码缺失/软链/越界: '+name)
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            fail('受测源码偏离固定基线: '+name)
    print('VERIFIED', root, 'baseline='+base, 'actual HEAD='+git(root,'rev-parse','HEAD'), flush=True)

def run(command, cwd, env, marker=None, stdin=None):
    print('RUN', ' '.join(map(str,command)), 'cwd='+str(cwd), flush=True)
    r = subprocess.run(command,cwd=cwd,env=env,input=stdin,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    print(r.stdout, end='', flush=True)
    if r.returncode or (marker and marker not in r.stdout):
        fail('检查失败或缺完成标记: '+str(command))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbench',required=True,type=Path)
    parser.add_argument('--media',required=True,type=Path)
    args=parser.parse_args()
    ui,media=args.workbench.resolve(),args.media.resolve()
    if ui==media or ui.is_relative_to(media) or media.is_relative_to(ui):
        fail('须显式提供两个独立、互不嵌套的检出目录')
    manifest=json.loads((HERE/'inputs.json').read_text())
    verify(ui,manifest['workbench']);verify(media,manifest['media'])
    node=shutil.which('node')
    if not node:fail('缺少离线 Node；不会安装')
    for name,version in manifest['dependencyVersions'].items():
        p=ui/'web/node_modules'/name/'package.json'
        if not p.is_file() or json.loads(p.read_text()).get('version')!=version:
            fail('缺少或版本不符的已有离线依赖: '+name+' '+version+'；不会安装')
    env=dict(os.environ)
    for key in ['NODE_OPTIONS','NODE_PATH','IMAGE_PAGE_SOURCE','AUDIO_PAGE_SOURCE']:
        env.pop(key,None)
    print('Node',subprocess.check_output([node,'--version'],text=True).strip(),flush=True)
    run([node,'tests/run-case-workspace-flow.cjs'],ui/'web',env,'PASS case flow:')
    run([node,'tests/report-explicit-case.test.cjs'],ui/'web',env,'PASS explicit-case actual Layout/ReportPage')
    for medium in ['image','audio']:
        run([node,'--test','--test-reporter=tap',f'tests_acceptance/{medium}-loaded-context/page.test.cjs'],media,env,'# fail 0')
    tree=ast.parse((media/'service/mcis_service/_review_page.py').read_text())
    if any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(tree)):
        fail('纯 HTML shaping 不得导入模块')
    scope={};exec(compile(tree,'<verified pure HTML shaping>','exec'),scope)
    pages={}
    with tempfile.TemporaryDirectory(prefix='mcis-offline-html-') as tmp:
        for medium in ['image','audio']:
            html=(media/f'service/mcis_service/{medium}_review/review.html').read_text()
            for enabled in [True,False]:
                mode='full' if enabled else 'limited'
                shaped=scope['_review_page'](html,task_routes=enabled)
                pages[medium+'-'+mode]=shaped
                page=Path(tmp)/(medium+'-'+mode+'.html');page.write_text(shaped)
                child={**env,medium.upper()+'_PAGE_SOURCE':str(page)}
                suites=['url-reopen','reopen-address','save-conflict']
                if medium=='image':suites.append('save-snapshot')
                for suite in suites:
                    run([node,'--test','--test-reporter=tap',f'tests_acceptance/{medium}-{suite}/page.test.cjs'],media,child,'# fail 0')
        run([node,'tests_acceptance/media-receipt-guidance/page.cjs'],media,env,'audio-limited:',json.dumps(pages))
    print('PASS OFFLINE REPRESENTATIVE CHECKS ONLY — 两条候选未整合；非浏览器/HTTP/身份/工作台切案验收',flush=True)

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('FAIL:',exc,file=sys.stderr);sys.exit(1)
