# Public two-role Pi research implementation — 2026-11-14

Base main3aba2bf03e393909c611489ae573a887087637ac; isolated branch
codex/public-expert-group-20261114. Only new research module, contract and workflow
records. No identity/evidence-file/timeline/hypothesis/archive implementation edits.

Fixed public YANGZE22 oil-loss section (PDF28/printed26), three claims; original
source text/locators retained, reference labels and author rationales omitted. Each
of source_attribution and uncertainty_boundary gets independent host/Pi histories,
read-only tools and bounded validation. Both opinions, exact quotes and uncertainty
remain side-by-side. Labels agreeing never activate facts or assert expert consensus.

Actual Pi core/ai1.5.2 are lockfile-pinned. Fixture uses two real Pi child loops but
scripted provider responses: six model protocol turns, four tools, zero external
provider requests. Fixed DeepSeek transport exists but real capability is NOT tested.
Secure environment credential presence check was false; no chat credential requested,
no real key supplied, no model call or provider fallback. Provider-labeled unit stubs
remain engineering tests, not live evidence.

Validation:
- `PYTHONPATH=.:research/expert_group service/.venv/bin/pytest -q research/expert_group`:
  **38 passed** (30 engine +8 CLI/export/render).
- Explicit CLI fixture run4cbb095f-1175-486b-bc9b-84ba1a1fb491: two role completions,
  each3 model turns/2tools; realPi=true, realModel=false, transportMocked=true,
  providerRequests=0, factActivated=false. `--verify-dir` passed local consistency.
- Original single-directory pytest command omitted the repository root from
  PYTHONPATH and failed collection. Correct reproducible command is above; not a
  product failure or passing test.
- Sandbox-enabled Chromium launch attempted before navigation to generated HTML;
  SUID helper misconfiguration aborted launch. No no-sandbox retry, permissions
  change, public listener or browser acceptance claim.

Pre-freeze review fixed two important boundaries: final receipt failure now forces
not_accepted instead of completed; HTTP and pipe writes use absolute time budgets
and cancel checks. Export result/page are provisional until completion.json matches
all file hashes and receipt terminal. Late write/fsync errors cannot create a valid
completion marker. Local chain/manifest are not signatures or authenticity proofs.

No automatic overwrite/retry. Incomplete role/provider outcomes remain failed,
cancelled or unknown and never count as completed group/model acceptance. Real model
acceptance and native browser/CSP/download behavior remain explicit outstanding gates.

## r1 coordinator-review correction

Coordinator reproduced a directory-leaf failure that leaked one raw descriptor per
verify attempt. receipt.read now validates regular-file type before wrapping, and
both read/write helpers explicitly retain ownership until fdopen succeeds, closing
any untransferred descriptor in finally. Four directory leaf cases each repeat four
times with no fd growth; injected fdopen failure on both helpers likewise does not
leak. Primary CLI suite is now13 cases (engine30 unchanged). New r1 freeze supersedes
the initial freeze, retained as historical evidence. Real DeepSeek remains paused;
no credentials or ready platform secret/outbound-identity bindings are available.
