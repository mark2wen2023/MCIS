# W15 blocked browser run: observe without changing the gate

Use this only for a bounded diagnostic rerun of the synthetic W15 negative
acceptance. It runs the SHA-256-checked `9ca1c12` runner itself, with the exact
same arguments and product pins. It changes no page readiness wait, sandbox
option, network route, assertion, artifact, or exit code. In particular it
does not use the earlier `domcontentloaded` probe as acceptance.

Replace only the runner path in the original Chrome command. Set an outer
watchdog, retain stderr, and use a never-used evidence directory:

```sh
timeout --signal=TERM --kill-after=10s 150s \
  python3 -B tests_acceptance/w15-source-chromium/diagnose.py \
  --source "$PWD" --node-modules /existing/web/node_modules \
  --host-python /existing/service/venv/bin/python --browser /existing/google-chrome \
  --evidence /new/w15-browser-diagnosis > /new/w15.stdout 2> /new/w15.stderr
```

The trace prints only pinned function names, line numbers, event names, and
elapsed time, with one Python stack dump at 45 seconds. No signal to the
Python process is needed to get that stack. Report the last trace lines and
stack, exact exit status, and whether the original command produced its
receipt and three originals. A timeout or only a mounted heading is not a
pass. The probe does not create a separate success result. Do not run on real
data, kill unrelated processes, or retry by reducing acceptance coverage.
