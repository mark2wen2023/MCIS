# Current follow-up: existing KnowledgeCard review entry

Base 568d4b0ea74efeb570cf406b52e3cdfc4b0d4f02. This revision changes the ACTUAL
KnowledgeCard used by KnowledgePage, not the standalone synthetic preview mount.
Only Candidate cards get the native collapsed summary “进入待审核查”.
Inside the existing details, three read-only manual steps precede the existing
KnowledgeSourceBody. No new requests, fetching, source URLs, fields, save or publish handlers.
Existing Candidate visibility and canReview action policy remain unchanged.
Published/Rejected/Withdrawn markup is unchanged. Existing approval form remains outside
this details and opening it does not acknowledge its checkboxes.
Details key includes card ID, content digest and status; React replacement should reset
native open state, but this lifecycle has NOT been browser-tested.

Linux validation: 34 SSR checks, existing W19.1 27 assertions, W19.2 guards, exit 0.
Of 16 comparison combinations, Candidate comparisons remove ONLY the declared summary
replacement and added review-step section before checking all remaining markup byte-for-byte.
Other statuses compare unchanged. Two new actual-card checks cover canReview false/true,
existing excerpt, pending labels and no new controls. SSR confirms no open attribute.
No DOM library was installed; actual mouse/keyboard opening, focus, browser visibility
and replacement lifecycle remain for coordinator testing. No real account/service/model.
The run commands below remain applicable. No W9 or W20 files changed.

## Previous shared-preview implementation record
# W19 shared source presentation — synthetic SSR candidate

Base: `1f76a060dcf30f2cc403b5ef22ccc35f9f1e7d0c`.
Scope: extract only existing KnowledgeCard body/source markup into
`web/src/knowledge/KnowledgeSourceBody.tsx`; the original page passes unchanged
props and retains all lifecycle metadata, links and actions. No parser, route,
permission, persistence, ranker or fixture edits.

The developer-only `Preview.tsx` uses the SAME component with only fixed
synthetic text, no URL, no persistent Card fields and no callbacks. It accepts
only the exact pinned three-state result. Undefined/null display unconfigured;
changed input rejects the whole preview. This is deliberately NOT a general
receipt schema or authority check. JSON field order changes may also reject.

## Run (offline; installed dependencies only)

At candidate repository root:
```sh
node research/w19_case_ranking/version_binding_preview/run.cjs
node research/w19_case_ranking/version_binding_preview/run.cjs --html > /tmp/w19-source-preview.html
sha256sum -c research/w19_case_ranking/version_binding_preview/SHA256SUMS
```

No model, fetch, service, browser, installation or inference. HTML is static
and has no script, anchors or inputs. No application route imports this preview.
The HTML export is a developer-controlled artifact, not a stored review receipt.

Without .git, export the baseline KnowledgePage.tsx at the base commit and use:
```sh
node research/w19_case_ranking/version_binding_preview/run.cjs \
  --baseline-page /path/to/fixed-KnowledgePage.tsx \
  --web-deps /path/to/existing/web/node_modules
```

The runner verifies baseline page blob
`28ae58a1a39a39c23397b84f93c6d175b3fa7451`, plus fixture/result SHA-256 from
the unchanged version_binding directory. Missing dependency is an error,
not an automatic download. No duplicate dependency source is committed.
The fixed repository source exports were used locally; --web-deps selected
existing esbuild 0.28.2 and React 19.3.1. Build outputs stay in memory.

## Actual checks

- 16 byte-identical before/after SSR combinations: four product Card statuses,
  public/synthetic source and canReview true/false; props are invented controls.
  Product links/actions remain exactly as before; only the research view has none.
- 13 further SSR checks: all three states, unassessed support/causation and pending;
  exact current/stale time text; no links/controls/credential fields;
  confirmed/supported/authenticated/old-promoted/URL/identity/missing-row inputs
  refused; null/undefined and valid-invalid-valid replacement retain no prior text.
- Existing W19.1: 27 assertions passed.
- Existing W19.2 preview binding/no-model/no-save checks passed.
- Explicit-export runner and static HTML export exit 0.
  The runner guards fetch and storage writes. Product imports use an explicitly
  empty localStorage test double, not real credentials.
- Replacement checks are separate pure renders, not browser lifecycle tests.

The fixed host selection and source digests remain developer-visible synthetic
controls. LOCATED means current fixed bytes match, not semantic support.
Stale claims remain labelled refused; missing binding remains missing.
All rows remain pending, unassessed and unauthenticated, with no review/save action.
No real-system authentication, source access, human judgment, visual/browser QA,
professional scoring or recall improvement is claimed. W20 and frozen 27 cards unchanged.

## Follow-up: per-card manual review tasks
Three existing frozen cards now carry separate pending human tasks: semantic support,
stale-version reconciliation, or missing identity binding. This is read-only guidance,
not completed human review, a write workflow, ranking or a production mount.
The existing shared KnowledgeSourceBody remains the same. No source data or parser changed.
Three added SSR checks examine each actual card, task, pending label and absence of actions.
