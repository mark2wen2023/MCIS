"""Offline LibreDWG adapter; caller supplies trusted installed executable."""
from pathlib import Path
import subprocess
import tempfile
import shutil
from .drawing_parser import parse_drawing, fingerprint

def convert_and_parse(path, executable='dwg2dxf', timeout=120):
    path = Path(path)
    original = parse_drawing(path)
    if original['document']['format'] != 'dwg' or original['document']['status'] == 'failed':
        return original
    exe = shutil.which(executable)
    if not exe:
        original['issues'].append('converter_unavailable')
        return original
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp)/'source.dwg'
        target = Path(tmp)/'converted.dxf'
        shutil.copyfile(path, source)
        if fingerprint(source) != original['document']['sha256']:
            original['issues'].append('source_changed')
            return original
        try:
            proc = subprocess.run([exe, '-o', str(target), str(source)], cwd=tmp, capture_output=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired):
            original['issues'].append('conversion_execution_failed')
            return original
        if proc.returncode or not target.is_file() or target.is_symlink():
            original['issues'].append('conversion_failed')
            return original
        parsed = parse_drawing(target)
        original['conversion'] = {'tool':'LibreDWG dwg2dxf', 'derivative_sha256':parsed['document']['sha256'], 'returncode':proc.returncode}
        original['entities'] = parsed['entities']
        original['units'] = parsed['units']
        original['document']['status'] = parsed['document']['status']
        original['issues'] = parsed['issues'] + ['derivative_handles_require_review']
        return original
