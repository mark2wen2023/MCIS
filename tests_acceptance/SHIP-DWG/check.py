"""实际运行已注册代码之外的离线验收，输出只存到操作者指定的新目录。"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import ezdxf
from compare import audit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'service'))
from mcis_service.agents.skills.ship_reconstruction.dwg_adapter import convert_and_parse
from mcis_service.agents.skills.ship_reconstruction.drawing_parser import fingerprint


def command(args, log):
    proc = subprocess.run(args, capture_output=True, timeout=180)
    output = proc.stdout + proc.stderr
    log.write_bytes(output)
    if proc.returncode != 0:
        raise ValueError(f'{args[0]} 退出 {proc.returncode}，详见 {log.name}')
    return sum(b'warning:' in line.lower() for line in output.splitlines())


def check_one(case, path, out):
    digest = fingerprint(path)
    if digest != case['sha256']:
        raise ValueError('原图指纹与基准不一致')
    out.mkdir()
    target = out/'converted.dxf'
    warnings = command(['dwg2dxf','-o',target,path],out/'dwg2dxf.log')
    with tempfile.TemporaryDirectory() as tmp:
        direct = Path(tmp)/'source.json'
        command(['dwgread','-O','JSON','-o',direct,path],out/'dwgread.log')
        result = audit(json.loads(direct.read_bytes()),target,case)
    result['warnings'] = warnings
    result['sha256'] = digest
    result['dxf_sha256'] = fingerprint(target)
    if fingerprint(path) != digest:
        raise ValueError('运行期间原图发生变化')
    parsed = convert_and_parse(path, executable='dwg2dxf')
    adapter_status = parsed['document']['status']
    derived = parsed.get('conversion',{}).get('derivative_sha256')
    entities = parsed['entities']
    result['adapter'] = {'status':adapter_status,'issues':parsed['issues'],
                         'entities':len(entities),'same_dxf':derived==result['dxf_sha256']}
    expected_count = case['modelspace_entities']
    adapter_handles = {(e['handle'],e['type']) for e in entities if e['layout'].lower()=='model'}
    cad = ezdxf.readfile(target)
    result['adapter']['modelspace_matched'] = adapter_handles == {(e.dxf.handle,e.dxftype()) for e in cad.modelspace()}
    result['scope_passed'] = (not result['differences'] and result['source_entities']==expected_count
                              and adapter_status=='partial' and result['adapter']['same_dxf']
                              and result['adapter']['modelspace_matched'])
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--modelspace-only',action='store_true',help='仅用模型空间比对决定退出码，仍生成跨空间报告')
    cli.add_argument('manifest',type=Path)
    cli.add_argument('drawings',type=Path)
    cli.add_argument('output',type=Path)
    args = cli.parse_args()
    cases = json.loads(args.manifest.read_text())['drawings']
    ids = [case['id'] for case in cases]
    if not ids or len(set(ids))!=len(ids) or any(not re.fullmatch(r'[A-Za-z0-9_-]+',k) for k in ids):
        raise ValueError('空清单、重复或无效的 ID')
    if not any(case.get('offset_values') for case in cases):
        raise ValueError('缺少型值表核对定位')
    out = args.output
    out.mkdir(parents=True,exist_ok=False)
    report = {'manifest_sha256':fingerprint(args.manifest),'converter':subprocess.check_output(
        ['dwg2dxf','--version'],text=True).strip(),'ezdxf':ezdxf.__version__,'drawings':{},
        'whole_document_approved':False}
    for case in cases:
        file = Path(case['file'])
        if file.name != str(file) or file.suffix.lower()!='.dwg':
            raise ValueError('原图清单应提供 DWG 文件名')
        try:
            result = check_one(case,args.drawings/file,out/case['id'])
        except (ValueError,OSError,KeyError,subprocess.SubprocessError,ezdxf.DXFError) as exc:
            result = {'scope_passed':False,'error':str(exc)}
        report['drawings'][case['id']] = result
        print(case['id'], '通过限定比对' if result['scope_passed'] else '待核查', flush=True)
    (out/'quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for result in report['drawings'].values():
        if not result['scope_passed']:
            return 4
        other = result['outside_modelspace']
        if not args.modelspace_only and (other.get('missing_handles',0) or
                other.get('texts_with_difference',0) > other.get('unicode_escape_only',0)):
            return 4
    return 0


if __name__=='__main__':
    sys.exit(main())
