"""Pinned no-network IPC fixture. A request does nothing until a host grant."""
import sys
import time

mode = sys.argv[1]
if mode not in ('two', 'three', 'duplicate', 'unknown'): raise SystemExit(9)
for n in ([1, 1] if mode == 'duplicate' else range(1, 4 if mode == 'three' else 3)):
    print(f'REQUEST {n}', flush=True)
    if sys.stdin.readline() != f'GRANT {n}\n': raise SystemExit(8)
    if mode == 'unknown': time.sleep(30)
    print(f'RESPONSE {n}', flush=True)
print('DONE', flush=True)
