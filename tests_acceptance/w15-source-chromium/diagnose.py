"""Observe the unchanged W15 negative gate; no alternate browser behavior."""
import faulthandler
import hashlib
from pathlib import Path
import runpy
import sys
import time


ORIGINAL_SHA256 = "0d962047ef4659e73fe1250d047e38639e9868a6f4c28f58cdc32da603efbfe0"
WATCHED = frozenset(("main", "host", "setup", "dump", "app_ui", "show"))


def observe(runner, watchdog_seconds=45):
    if not __debug__:
        raise RuntimeError("W15 refuses to run with assertions disabled")
    if hashlib.sha256(runner.read_bytes()).hexdigest() != ORIGINAL_SHA256:
        raise RuntimeError("W15 diagnostic requires the byte-exact response-observation runner")
    if sys.gettrace() is not None:
        raise RuntimeError("W15 diagnostic requires an unused trace hook")
    fixed_name = str(runner)
    started = time.monotonic()

    def log(frame, event, unused):
        code = frame.f_code
        if event == "call":
            if code.co_filename != fixed_name or code.co_name not in WATCHED:
                return None
        if event in ("call", "line", "exception", "return"):
            print(f"W15 TRACE +{time.monotonic() - started:.3f}s "
                  f"{code.co_name}:{frame.f_lineno} {event}", file=sys.stderr, flush=True)
        return log

    faulthandler.dump_traceback_later(watchdog_seconds, file=sys.stderr)
    try:
        sys.settrace(log)
        runpy.run_path(fixed_name, run_name="__main__")
    finally:
        sys.settrace(None)
        faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    observe(Path(__file__).resolve().with_name("run.py"))
