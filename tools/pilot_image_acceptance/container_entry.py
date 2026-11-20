"""Image build installs this file at /opt/pilot/entry.py. Never invoke on host.
Image review must freeze this entry, exact source/schema subset and dependencies;
no .pth/editable/sitecustomize/user packages or business assets may be included.
"""
import os
import sys
from pathlib import Path

if __name__=='__main__':
    if not sys.flags.isolated or Path(__file__).resolve()!=Path('/opt/pilot/entry.py'):
        raise SystemExit(2)
    # Dedicated original stdout carries ONE receipt. Suppress all library/child
    # stdout/stderr before business imports; no raw Docker logs are retained.
    channel=os.dup(1);os.set_inheritable(channel,False)
    with open(os.devnull,'wb') as sink:
        os.dup2(sink.fileno(),1);os.dup2(sink.fileno(),2)
    sys.path[:0]=['/opt/pilot/source','/opt/pilot/source/service']
    from tools.pilot_image_acceptance.runtime_host import main
    code=2
    try:
        code,raw=main()
        if len(raw)>2048:raise ValueError('receipt budget')
        os.write(channel,raw)
    except BaseException:code=2
    finally:os.close(channel)
    raise SystemExit(code)
