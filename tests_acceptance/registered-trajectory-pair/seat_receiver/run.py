"""Explicit local acceptance runner; disabled unless a mode and checkout are supplied."""
import functools,hashlib,importlib.util,runpy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location('_portable_'+name,HERE/(name+'.py'))
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
def main():
    if not sys.flags.isolated or len(sys.argv)!=3 or sys.argv[1] not in ('--check','--handoff'):
        raise SystemExit('DISABLED: use python -I -B run.py --check|--handoff /existing/checkout')
    objects=load('fixed_objects');repo=Path(sys.argv[2]).resolve()
    dependencies=objects.fixed_dependencies(repo)
    if sys.argv[1]=='--check':return load('check').run(dependencies)
    receiver=load('receiver')
    path=repo/'tests_acceptance/registered-trajectory-pair/seat_handoff.py'
    raw=path.read_bytes()
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob!='e43290ccf27af8e7126ac3edd6ab87d6236c61b1':raise ValueError('HOST_BLOB')
    # Existing host resolves its own sibling fixtures and local Git objects.
    return runpy.run_path(str(path))['run_handoff'](functools.partial(receiver.consumer,dependencies=dependencies))
if __name__=='__main__':raise SystemExit(0 if main() else 1)
