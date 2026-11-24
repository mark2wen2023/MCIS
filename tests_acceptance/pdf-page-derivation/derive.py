"""Local synthetic acceptance adapter; no route, authorization or official flags.
Caller must already hold authorized PDF bytes. Digests here are lineage checks,
not permission or authenticity. Only the fixed bounded rendering profile exists.
"""
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from PIL import Image

SPEC = {'format': 'PNG', 'dpi': 72, 'scaleTo': 256, 'pageBox': 'MediaBox'}


def sha(raw): return hashlib.sha256(raw).hexdigest()


def need(ok, reason):
    if not ok: raise ValueError(reason)


def invoke(executable, args, raw, cwd):
    result = subprocess.run([executable, *args], input=raw, capture_output=True,
                            timeout=15, cwd=cwd, env={'PATH': os.defpath, 'LC_ALL': 'C', 'HOME': cwd})
    need(result.returncode == 0 and not result.stderr.strip(), 'PDF tool failed')
    return result.stdout


def render(raw, *, expected_sha256, physical_page):
    need(type(raw) is bytes and 0 < len(raw) <= 2 * 1024 * 1024 and raw.startswith(b'%PDF-'), 'PDF input')
    need(type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}', expected_sha256) is not None
         and sha(raw) == expected_sha256, 'source digest mismatch')
    need(type(physical_page) is int and 1 <= physical_page <= 8, 'physical page')
    info, ppm = shutil.which('pdfinfo'), shutil.which('pdftoppm')
    need(info is not None and ppm is not None, 'installed Poppler required')
    with tempfile.TemporaryDirectory(prefix='synthetic-pdf-page-') as tmp:
        output = invoke(info, ['-'], raw, tmp).decode('utf-8', errors='strict')
        counts = re.findall(r'^Pages:\s+(\d+)\s*$', output, re.M)
        need(len(counts) == 1 and 1 <= int(counts[0]) <= 8, 'page count')
        need(physical_page <= int(counts[0]), 'page outside document')
        need(re.findall(r'^Encrypted:\s+(\S+)', output, re.M) == ['no'], 'encrypted PDF unsupported')
        # Input is stdin, output is a fixed name under our fresh directory.
        invoke(ppm, ['-f', str(physical_page), '-l', str(physical_page), '-singlefile',
                     '-r', '72', '-scale-to', '256', '-png', '-', 'page'], raw, tmp)
        path = Path(tmp) / 'page.png'
        need(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024 * 1024, 'page output')
        png = path.read_bytes()
    with Image.open(io.BytesIO(png)) as image:
        need(image.format == 'PNG' and image.width <= 256 and image.height <= 256 and image.width > 0 and image.height > 0, 'page dimensions')
        image.load()
        width, height = image.size
    return {'sourceSha256': expected_sha256, 'physicalPage': physical_page,
            'renderSpec': dict(SPEC), 'pageSha256': sha(png), 'width': width, 'height': height}, png


def crop(png, *, page_record, expected_source_sha256, expected_physical_page, box):
    need(type(page_record) is dict and set(page_record) == {'sourceSha256', 'physicalPage', 'renderSpec', 'pageSha256', 'width', 'height'}, 'page record')
    need(type(expected_physical_page) is int and type(page_record['physicalPage']) is int
         and page_record['physicalPage'] == expected_physical_page
         and page_record['sourceSha256'] == expected_source_sha256, 'page binding mismatch')
    need(page_record['renderSpec'] == SPEC and sha(png) == page_record['pageSha256'], 'derived bytes mismatch')
    need(type(box) is tuple and len(box) == 4 and all(type(n) is int for n in box), 'crop coordinates')
    with Image.open(io.BytesIO(png)) as image:
        image.load()
        need(image.format == 'PNG' and image.size == (page_record['width'], page_record['height']), 'derived dimensions')
        left, top, right, bottom = box
        need(0 <= left < right <= image.width and 0 <= top < bottom <= image.height, 'crop bounds')
        buffer = io.BytesIO()
        image.crop(box).save(buffer, format='PNG')
        raw = buffer.getvalue()
    return {'sourceSha256': expected_source_sha256, 'physicalPage': expected_physical_page,
            'pageSha256': page_record['pageSha256'], 'coordinateSpace': 'derived-page-pixels-top-left',
            'box': list(box), 'cropSha256': sha(raw)}, raw
