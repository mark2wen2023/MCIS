"""Image build installs this file at /opt/pilot/entry.py. Never invoke on host.
Image review must freeze this entry, exact source/schema subset and dependencies;
no .pth/editable/sitecustomize/user packages or business assets may be included.
"""
import sys
from pathlib import Path

if __name__=='__main__':
    if not sys.flags.isolated or Path(__file__).resolve()!=Path('/opt/pilot/entry.py'):
        raise SystemExit(2)
    sys.path[:0]=['/opt/pilot/source','/opt/pilot/source/service']
    from tools.pilot_image_acceptance.runtime_host import main
    raise SystemExit(main())
