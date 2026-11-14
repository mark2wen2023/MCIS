# Independent public UI acceptance harness review

Reviewed fixed-scope `public-ui-host.py`, the trusted `review_origin` constructor,
and `pi-public-ui-live.tsx`. Explicit fixture mode only: no actual API call,
credentials, deployment or browser-engine acceptance in this review.

## Fixed finding

The broker initially checked its total deadline only when waiting for another
stdin chunk, allowing already-buffered lines to bypass expiration. The author
added checks at read entry, before returning a line, after parsing/before dispatch,
and before emitting results. The independent buffered-expired-line reproduction
now rejects. Failed/unknown writes are not described as rolled back.

## Final frozen checks

- `test_pi_public_ui_broker_independent.py`: **12/12**, zero skips, 14.20s.
- `pi-public-ui-launcher-independent.py`: **3/3** actual subprocess checks passed.

Broker tests cover review/archive refusal before accepted Pi completion, forged
final rejection, post-completion Pi/generate/wrong-channel denial, import pinned
to the most recent server export, client review-origin refusal, scripted origin
retention, ordinary failure cleanup, explicit close before inference, cumulative
and single-line budgets, and expired buffered input.

Launcher checks cover invalid CLI, invalid stdin with sentinel content, no sentinel
in stdout/stderr/receipt files, and complete actual Pi + mocked provider -> Python
broker + SQLite -> React/HappyDOM -> scripted review/remount -> v2 archive
export callback/File import/list/read -> cleanup acknowledgment -> child exit0 ->
accepted receipt. Receipt ordering was inspected; no child temporary storage
remained on the normal completion path. The fixture reports realModel=false,
mockInference=true, providerRequests=0, browserEngine=false and
reviewActor=scripted_test_not_human.

Earlier changing-bundle test failure was due to the implementer replacing raw
JSON.stringify equality with structural key-order comparison of complete
proposals/citations. The comparison does not rewrite payloads. Final frozen
source/bundle rerun passed; a separate earlier fixture run also passed.

## Boundaries retained

- Key via stdin only, no model/source/error payloads in receipt or failure logs.
- Only original read/validate tools are model-visible; UI writing is explicit
  fixed trusted RPC after model acceptance, not an agent write tool.
- Review origin comes from trusted construction, never client RPC input.
- Restored archive remains untrusted and inactive; no fact approval.
- HappyDOM interaction is not browser-engine, disk download or production login.
- Cleanup is verified on normal success/handled errors, not SIGKILL/container loss.
- A future live run must be reported separately from these mocked-provider checks.
9ffdc6c22a4c2e2c299716e46c1b49125770533fadc249d15ed516676023bb49  pi-transcript/runtime/public-ui-host.py
d1426a448100752da9465904b107779e3dbde3e58b4b89db37bc35f54f7b58a1  issue-ui/web/tests/pi-public-ui-live.tsx
3f37ed67b8af4c218c69fc7f2fdde155a3eab486c0cd13fc056b73d5e1543fe4  pi-transcript/service/mcis_service/agents/persistent_extraction_review_host.py
