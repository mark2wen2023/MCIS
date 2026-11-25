#!/usr/bin/env bash
# usage: run_e2e.sh <viewport> <tag>   (from anywhere). Backend+frontend both from the 29cbfe2 worktree.
set -u; W=/workspace/mcis-w17-chr-29cbfe2; R=/workspace/mcis-w17-chr-report; T=$R/tooling; VP=$1; TAG=$2; D=/tmp/w17b-$TAG
PW=/usr/local/lib/pnpm/5/.pnpm/playwright@1.63.0-alpha-2026-08-31/node_modules/playwright
rm -rf $D; (cd $W && exec service/.venv/bin/python -B $T/e2e_server.py --repo $W --data $D --port 18773 > $R/logs/05-e2e-$TAG-backend.log 2>&1) & BP=$!
(cd $W/web && MCIS_API=http://127.0.0.1:18773 exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 18774 --strictPort) > $R/logs/05-e2e-$TAG-vite.log 2>&1 & VPID=$!
for i in $(seq 200); do [ -f $D/ready.json ] && curl -sf http://127.0.0.1:18774/ >/dev/null && break; sleep .1; done
ss -ltn | grep -E ':1877[34] ' > $R/logs/05-e2e-$TAG-listeners.txt
node $T/e2e_driver.cjs $PW /opt/google/chrome/google-chrome $D/ready.json http://127.0.0.1:18774 $VP $R/screenshots $TAG > $R/logs/05-e2e-$TAG.json 2>$R/logs/05-e2e-$TAG.stderr; RC=$?
kill $VPID $BP; wait $VPID $BP 2>/dev/null; echo $RC > $R/logs/05-e2e-$TAG.exit; exit $RC
