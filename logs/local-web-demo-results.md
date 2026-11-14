# Local web demo final validation

Base118db4dcb52445de01425274a3f97af7783c83d1. Independent safety design approved
before implementation; separate independent implementation/DOM review.

Primary13+independent18=31/31 zero skips. Final prior400+terminal17+web31=448/448
zero skips124.79s (counts overlap with earlier runs). Actual core enabled via
MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh. Relevant new tests:
service/tests/test_web_demo.py and test_web_demo_independent.py. Prior tests unchanged.
Actual CLI child+loopback urllib POST both returned sources2/delta5deg/unreviewed/
temporaryDataCleaned=true in both primary and independent executions.

Primary and independent HappyDOM scripts pass. Independent covers17 rejected summary
mutations plus overlapping/late completion locks, choice invalidation and single
source positive. Node scripts are simulated DOM/fetch, not actual browser network.
No product changes after final runs; sha256 web_demo.py:
9cddeea75e3d7d804de6747df759602bc59cc9f38c9fb161a0ffaad6b19ac278
and demo.js:3a73d3f468fd0d29a6b2ecb569383b12d32f228c2061f617184a134c59f4ccb3.

CUA cloud browser actual navigation to running execution-loopback URL failed
net::ERR_CONNECTION_REFUSED. No screenshots, real browser clicks/console/render,
responsive visual or browser CSP enforcement pass claimed. No public tunnel or
relaxed controls used. Actual same-process child HTTP worked separately. Local
manual test server stopped (exit130); independent child terminated after checks.

Standalone explicit loopback fictional demo, not hosted/deployed product. No real
credentials/real evidence/protected intake UI/production login/IdP/LLM/general proxy.
Default protected entry remains closed and old app unmounted. Normal task cleanup
and shield drain tested, not forced kill/power-loss. No merge/deployment.
