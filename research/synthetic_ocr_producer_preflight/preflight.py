"""Read-only static checks. Never import Paddle, initialize, infer or download."""
import argparse,hashlib,importlib.metadata,json,tarfile
from pathlib import Path,PurePosixPath
PACKAGES={'paddlepaddle':'3.2.0','paddleocr':'3.3.2','paddlex':'3.3.13'}
MODELS={'PP-OCRv5_mobile_det':'50446e5d01ac2a73d5319c89513281f6578414c888c602f9af13f93feefffc58','PP-OCRv5_mobile_rec':'566b9512b34e34a9f0db54d87b51fa5a0b9ed2cf1ab7e49728cc0b8b5a64f414'}
IMAGES={'poppler-1.png':'004e445bdeb0536d14eed7ca765d477eb9fb6bf12db18daa3cd82a27744701c8','poppler-2.png':'60cdfab7def30e761f2f0f446e798b1d8fbdb6eff6e96fed4b7aaac2a83359fb'}
REQUIRED={'inference.json','inference.pdiparams','inference.yml'}
def digest_stream(s):
    h=hashlib.sha256()
    for b in iter(lambda:s.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def digest(p):
    with p.open('rb') as f:return digest_stream(f)
def archive_check(root,name,expected):
    p=root/(name+'.tar')
    try:
        if digest(p)!=expected:return 'archive_hash_mismatch'
        seen=set();required=set()
        with tarfile.open(p) as tar:
            for entry in tar:
                path=PurePosixPath(entry.name)
                if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0]!=name+'_infer':return 'archive_layout_rejected'
                if entry.isdir():continue
                if not entry.isfile() or entry.name in seen:return 'archive_layout_rejected'
                seen.add(entry.name)
                local=root.joinpath(*path.parts)
                if not local.resolve().is_relative_to(root.resolve()):return 'local_layout_rejected'
                with tar.extractfile(entry) as source:
                    if digest_stream(source)!=digest(local):return 'extracted_bytes_mismatch'
                if len(path.parts)==2:required.add(path.name)
        if not REQUIRED<=required:return 'required_members_missing'
        return 'archive_and_extracted_bytes_match'
    except FileNotFoundError:return 'missing'
    except (OSError,tarfile.TarError):return 'unreadable_or_invalid_archive'
def _check(root,images,versions,model_pins,image_pins):
    packages={}
    for p,expected in PACKAGES.items():
        try:v=versions(p)
        except importlib.metadata.PackageNotFoundError:v=None
        packages[p]={'expected':expected,'observed':v,'match':v==expected}
    models={n:archive_check(root,n,h) for n,h in model_pins.items()}
    renders={}
    for n,h in image_pins.items():
        try:renders[n]='match' if digest(images/n)==h else 'hash_mismatch'
        except FileNotFoundError:renders[n]='missing'
        except OSError:renders[n]='unreadable'
    ok=all(x['match'] for x in packages.values()) and all(x=='archive_and_extracted_bytes_match' for x in models.values()) and all(x=='match' for x in renders.values())
    return {'status':'static_inputs_match_runtime_unverified' if ok else 'blocked','staticInputsMatch':ok,'readyForInference':False,'packages':packages,'models':models,'renders':renders,'modelImported':False,'inferenceRun':False,'networkUsed':False,'remaining':['transitive dependency and native ABI compatibility','CPU operator initialization and execution','approved synthetic producer entry: public-page6 runner remains incompatible','verified crop/rotation processing provenance']}
def check(root,images):return _check(root,images,importlib.metadata.version,MODELS,IMAGES)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model-root',type=Path,required=True);p.add_argument('--images',type=Path,required=True);a=p.parse_args()
    r=check(a.model_root,a.images);print(json.dumps(r,indent=2));raise SystemExit(0 if r['staticInputsMatch'] else 2)
