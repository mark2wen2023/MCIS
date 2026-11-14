"""Internal digital PDF text-layer derivation; not OCR, service or security sandbox."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import tempfile
import time

class DerivationError(Exception):
    pass

@dataclass(frozen=True)
class Limits:
    input_bytes: int = 8 * 1024 * 1024
    pages: int = 100
    page_text_bytes: int = 512 * 1024
    total_text_bytes: int = 4 * 1024 * 1024
    seconds: float = 30


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run_bounded(args, *, deadline, limit):
    """Bound combined stdout/stderr and wall time; not CPU/memory sandbox."""
    proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          env={**os.environ,'LC_ALL':'C'},start_new_session=True)
    data={'out':bytearray(),'err':bytearray()};sel=selectors.DefaultSelector()
    try:
        for name,stream in [('out',proc.stdout),('err',proc.stderr)]:
            os.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,name)
        while sel.get_map():
            remaining=deadline-time.monotonic()
            if remaining<=0:raise DerivationError('time_budget')
            for key,_ in sel.select(min(remaining,.1)):
                b=os.read(key.fileobj.fileno(),65536)
                if not b:sel.unregister(key.fileobj);continue
                data[key.data].extend(b)
                if sum(map(len,data.values()))>limit:raise DerivationError('output_budget')
        remaining=deadline-time.monotonic()
        if remaining<=0:raise DerivationError('time_budget')
        try:code=proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:raise DerivationError('time_budget') from None
        if code:raise DerivationError('parser_failed')
        # Warnings are not silently converted to successful partial extraction.
        return bytes(data['out']),bytes(data['err'])
    finally:
        # Descendants may still hold pipes after the process-group leader exits.
        import signal
        try:
            os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        sel.close();proc.stdout.close();proc.stderr.close()


def derive(pdf_bytes,limits=Limits()):
    """Return complete versioned artifact or fail with no partial publication.

    Input is an immutable caller-provided authorized snapshot; evidence identity,
    storage, auth and provenance verification are caller responsibilities.
    """
    if type(pdf_bytes) is not bytes:raise DerivationError('immutable_bytes_required')
    if type(limits) is not Limits:raise DerivationError('invalid_limits')
    for v in (limits.input_bytes,limits.pages,limits.page_text_bytes,limits.total_text_bytes):
        if type(v) is not int or not 1<=v<=100*1024*1024:raise DerivationError('invalid_limits')
    if type(limits.seconds) not in (int,float) or not 0<limits.seconds<=300:raise DerivationError('invalid_limits')
    if not pdf_bytes or len(pdf_bytes)>limits.input_bytes:raise DerivationError('input_budget')
    if not pdf_bytes.startswith(b'%PDF-'):raise DerivationError('invalid_pdf_header')
    texttool=shutil.which('pdftotext');infotool=shutil.which('pdfinfo')
    if not texttool or not infotool:raise DerivationError('parser_unavailable')
    deadline=time.monotonic()+limits.seconds
    _,version=run_bounded([texttool,'-v'],deadline=deadline,limit=16384)
    version=version.decode('utf-8',errors='strict').splitlines()[0]
    with tempfile.TemporaryDirectory(prefix='mcis-text-layer-') as tmp:
        src=Path(tmp)/'snapshot.pdf';src.write_bytes(pdf_bytes);src.chmod(0o400)
        info,warn=run_bounded([infotool,str(src)],deadline=deadline,limit=65536)
        if warn.strip():raise DerivationError('parser_warning')
        if not re.search(rb'^Encrypted:\s+no\s*$',info,re.M):raise DerivationError('encrypted_or_unknown')
        match=re.search(rb'^Pages:\s+(\d+)\s*$',info,re.M)
        if not match:raise DerivationError('unknown_page_count')
        count=int(match[1])
        if not 1<=count<=limits.pages:raise DerivationError('page_budget')
        pages=[];used=0
        for n in range(1,count+1):
            raw,warn=run_bounded([texttool,'-f',str(n),'-l',str(n),'-layout','-enc','UTF-8',str(src),'-'],
                                deadline=deadline,limit=limits.page_text_bytes)
            if warn.strip():raise DerivationError('parser_warning')
            used+=len(raw)
            if used>limits.total_text_bytes:raise DerivationError('total_text_budget')
            try:text=raw.decode('utf-8',errors='strict')
            except UnicodeDecodeError:raise DerivationError('invalid_text_encoding') from None
            pages.append({'physicalPage':n,'text':text,'textSha256':sha(raw),'byteLength':len(raw),
                          'status':'text_layer_present' if text.strip() else 'no_selectable_text'})
        if src.read_bytes()!=pdf_bytes:raise DerivationError('source_changed')
    return {'format':'mcis-digital-pdf-text-layer','version':1,'sourcePdfSha256':sha(pdf_bytes),
            'sourceByteLength':len(pdf_bytes),'method':'embedded_text_only','tool':version,
            'parameters':['-layout','-enc','UTF-8'],'pageCount':count,'pages':pages,
            'warnings':['Not OCR or image understanding. Text-bearing pages can contain unextracted image regions.',
                        'Physical PDF pages are not printed page numbers. No completeness or factual accuracy claim.']}
