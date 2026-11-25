"""Materialize fixed W11 service, original and UI; run the isolated acceptance gate."""
import argparse
from hashlib import sha1
import os
from pathlib import Path
import runpy
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE=Path(__file__).resolve().parent
BASE="d9187fef1f979866ac4d8ce2064d1ac92f34bb36"
PRIOR=HERE.parent/"w11-excerpt-binding-local"
WEB=(
    ("web/src/ecfcDrafts/EdgeSelection.tsx","23b43a697ada26a87a5f5a7a418c59356aa07db6"),
    ("web/src/ecfcDrafts/Graph.tsx","7a68c9cb721a265b1c67c940044288daee77c52c"),
    ("web/src/ecfcDrafts/model.ts","aee50d3472990fdc69aed5ea8e33c78938db66ac"),
)

def main():
    if not __debug__: raise RuntimeError("Do not use Python -O")
    inherited=runpy.run_path(str(PRIOR/"run.py"))
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--repository",type=Path,action="append")
    group.add_argument("--source-dir",type=Path,action="append")
    p.add_argument("--browser",action="store_true")
    p.add_argument("--verify-only",action="store_true")
    args=p.parse_args()
    if args.repository: args.repository=[x.resolve() for x in args.repository]
    if args.source_dir: args.source_dir=[x.resolve() for x in args.source_dir]
    manifest=(PRIOR/"SOURCES").read_text("utf-8").splitlines()
    if len(manifest)!=186: p.error("Incomplete service/source manifest")
    with TemporaryDirectory(prefix="mcis-w11-edge-fixed-") as tmp:
        root=Path(tmp)
        def save(item,data):
            path=root/item
            if path.exists(): p.error(f"duplicate path: {item}")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        for line in manifest:
            save(*inherited["get_blob"](line,args,p))
        for item,pin in WEB:
            if args.source_dir:
                data=next((x.joinpath(item).read_bytes() for x in args.source_dir if x.joinpath(item).is_file()),None)
            else:
                data=None
                for repo in args.repository:
                    r=subprocess.run(["git","-C",str(repo),"-c","protocol.allow=never","cat-file","blob",f"{BASE}:{item}"],capture_output=True,env={**os.environ,"GIT_NO_LAZY_FETCH":"1","GIT_TERMINAL_PROMPT":"0","GIT_ALLOW_PROTOCOL":""})
                    if r.returncode==0:
                        data=r.stdout
                        break
            if data is None: p.error(f"Missing pinned UI source: {item}")
            if sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=pin:
                p.error(f"Pinned UI mismatch: {item}")
            save(item,data)
        print(f"W11 pins: {len(manifest)} service/original + {len(WEB)} UI; no fetch",flush=True)
        if args.verify_only: return 0
        env={**os.environ,"MCIS_FIXED_SERVICE":str(root/"service"),"MCIS_FIXED_WEB":str(root/"web"),
             "MCIS_W11_SYNTHETIC_ORIGINAL":str(root/inherited["CORE_MARKER"])}
        command=["bash",str(HERE/"run.sh")]+(["--browser"] if args.browser else [])
        return subprocess.run(command,env=env,check=False).returncode

if __name__=="__main__":
    raise SystemExit(main())
