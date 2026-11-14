# Integration handoff: knowledge slices (no merge performed)

All four drafts fork research/sk-t01-preview-20261113 at254167e3, not main.
They are narrow features, not four completed end-user workflows.

## Draft inventory and sequence
1. PR60 exact duplicate preview: only slice with an actual API route. New
duplicates.py + existing knowledge/router.py append, OpenAPI, REQUESTS/ROADMAP.
Integrate after reviewing current branch's route/schema changes. Internal-only
declared-role boundary remains non-production auth. UI still missing.
2. PR62 public source manifest: standalone local CLI + contract/tests. Use as
optional pre-import source declaration checker. No DB import, no parser and no
claim of authoritative/public source. Can integrate independently. Shared
REQUESTS/ROADMAP appends must be combined rather than overwrite each other.
3. PR65 source freshness: standalone callable with captured-time declarations,
version binding, exact source field comparison. No route/store/UI. Depends on a
future trusted source-snapshot capture/storage boundary for operational value.
No direct code dependency on PR62, and hashes across them are not interchangeable:
PDF byte hash, full candidate content hash, canonical source-field hash and
manifest hash identify DIFFERENT things.
4. Current worksheet: uses existing router.validate_content and digest helpers,
but edits no shared router. Internal JSON export only, not a formal decision.
Can integrate independently; UI/API delivery and review persistence remain.

## Conflicts
PR60 modifies shared knowledge/router.py, so reconcile with all concurrent route
work rather than replacing files. PR60 and PR62 both append shared planning docs;
resolve by preserving both additions. PR65/current add unique module, contract,
test and acceptance paths. Their only runtime coupling is existing W19 helper
semantics. Freeze helper/schema compatibility before integration.
No unrelated branch edits should be pulled merely to make tests green.

## Single end-user workflow still to build
- Authenticated candidate detail view with role-based authorized retrieval.
- Read-only duplicate preview near candidate creation, no automatic merge.
- Trusted source snapshot capture/storage: who/when/where/how and digest,
  preserving unknowns; no external query initiated by imported instructions.
- Freshness panel compares original/current snapshots and displays unavailable,
  changed or identical supplied fields. Unknown capture time remains visible;
  identical never implies currentness/authenticity/rights verified.
- Internal worksheet download from the actual authorized card, with digest binding,
  safe JSON download/content disposition and text-only rendering. No public leak
  of arbitrary caller content or internal audit actors/notes.
- Reviewer returns to current card, re-reads version and explicitly completes
  existing approvals. Worksheet and freshness utilities MUST NOT bypass the
  current lead-investigator review path or convert pending items into approvals.
- Store actual human decisions/check evidence using approved schema/migrations,
  not these generated pending worksheets; retain version and audit linkage.

## Integration verification gates
- Run current branch full relevant W19/archive suites and route/OpenAPI parity;
  baseline known missing registered-align-preview OpenAPI test is separate debt,
  not proof of these slices failing or excuse to hide a new regression.
- Role matrix, denied-source/card handling, stale content409, missing/unavailable
  snapshots, no automatic approval, safe source rendering and download authorization.
- Browser tests of create -> duplicate -> review worksheet -> changed snapshot ->
  explicit publish/reject/withdraw; verify external readers cannot access internal
  artifacts. Current standalone unit passes do not satisfy this gate.
- Real DeepSeek/public-case evaluation belongs to LLM-producing workflow, not
  these deterministic comparators; distinguish it from protocol fixtures.
- Verify reviewed final commit and CI independently; parent decides merge.
  No deployment authorized here.
