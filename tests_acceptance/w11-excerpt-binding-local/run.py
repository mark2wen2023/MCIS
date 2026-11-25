"""Only materialize exact local Git blobs before running the synthetic trial."""
import argparse
from hashlib import sha1
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
CORE_MARKER = "tests_acceptance/w11-t109-registered-source/communication.txt"
BOOT = """import runpy, sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
test=root/'trial'/'check.py'
sys.path[:0]=[str(root/'fixed'/'service'),str(test.parent)]
sys.argv=[str(test),str(root/'fixed'/sys.argv[2])]
runpy.run_path(str(test),run_name='__main__')
"""

def get_blob(line, args, parser):
    blob, commit, name = line.split()
    item = Path(name)
    if item.is_absolute() or name != item.as_posix() or ".." in item.parts or not item.parts or not re.fullmatch(r"(?:service|contracts|tests_acceptance)/[\w./-]+",name):
        parser.error(f"Invalid pinned path: {name}")
    if not all(re.fullmatch(r"[0-9a-f]{40}", spec) for spec in (blob,commit)):
        parser.error(f"Invalid pin for {name}")
    if args.source_dir:
        paths=[root/item for root in args.source_dir if (root/item).is_file()]
        if not paths:
            parser.error(f"Missing local pinned export: {name}")
        data=paths[0].read_bytes()
    else:
        env={**os.environ,"GIT_NO_LAZY_FETCH":"1","GIT_TERMINAL_PROMPT":"0","GIT_OPTIONAL_LOCKS":"0","GIT_ALLOW_PROTOCOL":""}
        spec=f"{commit}:{name}"
        for repository in args.repository:
            r=subprocess.run(["git","-C",str(repository),"-c","protocol.allow=never","cat-file","blob",spec],
                             capture_output=True,env=env,check=False)
            if r.returncode==0:
                data=r.stdout
                break
        else:
            parser.error(f"Missing local Git blob {spec}; no fetch attempted.")
    if sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=blob:
        parser.error(f"Pinned Git blob mismatch: {name}")
    return item,data

def main():
    if not __debug__: raise RuntimeError("Do not use Python -O")
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--repository",type=Path,action="append",help="existing local MCIS clone, repeat for multiple object stores")
    group.add_argument("--source-dir",type=Path,action="append",help="existing pinned bytes export, repeat for disjoint paths")
    p.add_argument("--verify-only",action="store_true",help="check all file hashes without importing service")
    args=p.parse_args()
    found=set()
    with TemporaryDirectory(prefix="mcis-w11-excerpt-fixed-") as temp:
        root=Path(temp)
        for line in (HERE/"SOURCES").read_text("utf-8").splitlines():
            item,data=get_blob(line,args,p)
            if item in found: p.error(f"Duplicated pin {item}")
            found.add(item)
            path=root/"fixed"/item
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        if len(found)!=186 or Path(CORE_MARKER) not in found:
            p.error("Incomplete pin manifest for authorized fixture")
        print(f"W11 pins: {len(found)} exact Git blobs; no network",flush=True)
        if args.verify_only: return 0
        trial=root/"trial"
        trial.mkdir()
        for name in ("check.py","pilot.py"):
            shutil.copyfile(HERE/name,trial/name)
        environment={k:v for k,v in os.environ.items() if k in ("HOME","PATH","LANG","LC_ALL","LD_LIBRARY_PATH","TMPDIR")}
        return subprocess.run([sys.executable,"-I","-B","-c",BOOT,str(root),CORE_MARKER],
                              cwd=root,env=environment,check=False).returncode

if __name__=="__main__":
    raise SystemExit(main())
