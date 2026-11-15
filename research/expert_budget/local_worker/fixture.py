"""Fixed local process fixture: no network, inputs, files, credentials or models."""
import sys
import time

if sys.argv[1:] == ['ok']:
    print('MCIS_LOCAL_FIXTURE_OK', flush=True)
elif sys.argv[1:] == ['fail']:
    raise SystemExit(7)
elif sys.argv[1:] == ['wait']:
    time.sleep(30)
else:
    raise SystemExit(9)
