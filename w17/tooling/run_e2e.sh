#!/usr/bin/env bash
# usage: run_e2e.sh <viewport> <tag>
set -u
W=/workspace/mcis-w17-871db66
R=/workspace/mcis-w17-871db66-report
T=$R/tooling
VP=$1; TAG=$2; D=/tmp/w17-871-$TAG
PW=/usr/local/lib/pnpm/5/.pnpm/playwright@1.63.0-alpha-2026-08-31/node_modules/playwright
rm -rf $D
(cd $W && exec service/.venv/bin/python -B $T/e2e_server.py --repo $W --data $D --port 18783 > $R/logs/03-e2e-$TAG-backend.log 2>&1) & BP=$!
(cd $W/web && MCIS_API=http://127.0.0.1:18783 exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 18784 --strictPort) > $R/logs/03-e2e-$TAG-vite.log 2>&1 & VPID=$!
for i in $(seq 200); do [ -f $D/ready.json ] && curl -sf http://127.0.0.1:18784/ >/dev/null && break; sleep .1; done
ss -ltn | grep -E ':1878[34] ' > $R/logs/03-e2e-$TAG-listeners.txt
node $T/e2e_driver.cjs $PW /opt/google/chrome/google-chrome $D/ready.json http://127.0.0.1:18784 $VP $R/screenshots $TAG > $R/logs/03-e2e-$TAG.json 2>$R/logs/03-e2e-$TAG.stderr
RC=$?
kill $VPID $BP 2>/dev/null
wait $VPID $BP 2>/dev/null
echo $RC > $R/logs/03-e2e-$TAG.exit
exit $RC
