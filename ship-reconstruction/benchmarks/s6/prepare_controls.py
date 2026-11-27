"""Prepare two fresh offline negative-control environments from a platform wheel lock."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

def setup():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--wheelhouse', type=Path, required=True)
    parser.add_argument('--dest', type=Path, required=True)
    options = parser.parse_args()
    options.dest.mkdir(parents=True, exist_ok=False)
    lines = options.lock.read_text().splitlines()
    for policy in ('no-igl', 'no-cgal'):
        folder = options.dest / policy
        subprocess.run([sys.executable, '-m', 'venv', folder], check=True)
        python = folder / 'bin/python'
        lock = folder / 'control.lock'
        lock.write_text('\n'.join(l for l in lines if policy != 'no-igl' or not l.startswith('libigl==')) + '\n')
        subprocess.run([python, '-m', 'pip', '--disable-pip-version-check', 'install', '--no-index',
                        '--find-links', options.wheelhouse.resolve(), '--require-hashes', '-r', lock], check=True)
        if policy == 'no-cgal':
            cgal = Path(subprocess.check_output([python, '-c', 'from igl.copyleft import cgal; print(cgal.__path__[0])'], text=True).strip())
            if not cgal.resolve().is_relative_to(folder.resolve()):
                raise ValueError('refuse to move a module outside the disposable environment')
            cgal.rename(folder / 'withheld_cgal')
        test = """import importlib.util, json
have_igl = importlib.util.find_spec('igl') is not None
try:
    from igl.copyleft import cgal
    have_cgal = callable(cgal.remesh_self_intersections)
except ImportError:
    have_cgal = False
print(json.dumps(dict(igl=have_igl,cgal=have_cgal)))
"""
        actual = json.loads(subprocess.check_output([python, '-c', test], text=True))
        assert actual == dict(igl=policy == 'no-cgal', cgal=False)
        (folder / 'state.json').write_text(json.dumps(actual) + '\n')
if __name__ == '__main__':
    setup()
