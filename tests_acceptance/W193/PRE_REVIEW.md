# W19.3 independent design pre-review

Date: 2026-11-12. Reviewed `contracts/W19.3-imo-condition-preview.md` independently. This is an engineering/source-consistency review, **not qualified maritime-law or competent-authority approval**. No runtime implementation, test pass, or browser acceptance is claimed.

## Disposition

**Do not implement the proposed §2.9 → §2.22 → §5/6 condition-result pipeline yet.** The proposal correctly stops before this step. It has useful investigation-support potential, but currently its fact ontology and four-valued aggregation are not complete enough to freeze as a rule contract. Adding `reviewRequired` cannot correct a misleading rule result.

A narrower, non-inferential **evidence-gap worksheet** is safe to design now: investigator assertions remain assertions; the UI can group them by clause and show missing/conflicting evidence and exact provenance. It must not compute the compound marine-casualty, marine-incident, very-serious or obligation predicates. This can be useful as a preparation/review aid, but a synthetic-only worksheet is not proof of operational usefulness. Do not build it merely to populate Sunday's UI if the owner prefers expert questions first.

## Source checks

Independently opened official [MSC.255(84)](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MSCResolutions/MSC.255%2884%29.pdf): §2.9/2.10 (printed7–8), §2.16/2.18/2.19 (9), §2.22/5 (10–11), §6/7 (11–12), §17 (16). Clause locations in proposal are consistent, except any source locator covering §7.5 should include printed12. No verbatim clause reproduction is necessary.

Relevant source distinctions: definitions permit an event sequence, not only isolated events. External-infrastructure damage has an additional safety-danger condition; the environmental branch links damage/potential damage to ship damage. §2.22 is nested under marine casualty. §17 means a negative §6 screen is not a general no-investigation finding. These distinctions support the blockers below, not a new authoritative interpretation.

## Blocking findings before compound-condition implementation

### P1: event versus event sequence and consequential association

One `eventId` is neither necessary nor sufficient to establish legal association. A legitimate sequence may span events; forcing every condition into one event can undercount. Conversely, assigning two facts the same ID does not prove that a death is involved in the casualty. The proposed test “related scrape plus unrelated death” is essential, but cannot be solved merely with a same-key join.

Required expert decision: define an explicitly asserted occurrence/sequence boundary, membership and association statements, with their provenance and unresolved alternatives. Decide whether and how these assertions support §2.9 versus §2.22. No automatic cross-event joining, and no automatic dismissal merely because distinct event IDs were used.

### P2: all branch-specific qualifiers must exist in the frozen schema

The present “minimum condition groups” do not explicitly represent the extra qualifiers of §2.9.6 and §2.9.7. A generic “damage + direct operational relation” representation could produce false support. The future schema needs a reviewed per-subclause expression and a complete list of qualified terms, not seven opaque consequence checkboxes.

Related: §2.10 needs an explicit danger/counterfactual-danger assertion, operational association, deliberate-harm exclusion and a robust “other than casualty” assessment. The current model does not list its danger fields. A lack of supplied casualty evidence cannot establish its negative premise.

### P3: four-valued calculus and provenance are underspecified

Decide whether states are entered by a user or derived from a set of assertions; if derived, specify duplicate/conflicting sources, empty assertions, source changes and conflicts of scope. `supported_by_input` must not erase a conflicting subordinate input. A clause can have one sufficiently supported branch and unresolved alternatives; use separate overall/completeness/conflict facets if appropriate rather than silently treating all conflicts as the same logical value.

Freeze a truth table and input-to-row trace rules before code. Avoid treating a document titled “assessment” or an asserted role label as authentication of a competent assessment. `expert confirmed` is a provenance claim unless the implementation verifies an actual review workflow.

### P4: review assistance must not delay action or imply a complete obligation inventory

§5.3 should remain visible independent of completion, not merely after a supported result. Label §5 output as international inter-State notification references, not a ship master's domestic reporting workflow. Never require all worksheet fields to be completed before a user can read the relevant notification source. Keep §17/other-regime caveats outside collapsible detail.

## Safe immediate deliverable

The current design and Q1–Q7 are a sound expert brief after adding P1–P3 detail. A practical expert packet should include four synthetic counterexamples and ask for decisions rather than answers that the software has already selected:

1. A related collision and a death of disputed association in one case.
2. A genuinely related casualty sequence spanning two recorded events.
3. External-infrastructure damage without an agreed serious-danger assessment.
4. Environmental harm with disputed ship-damage connection and no confirmed competent-State assessment.

For each, capture alternative interpretations, relevant clause identifiers and the fact needed to resolve the difference. No severity labels, “no duty”, recipients or deadlines. These are actionable review questions, not fake completion of W19.

If an evidence-gap worksheet is later chosen, acceptance must separately prove: no condition inference; no automatic join/negative inference; display of every provided contradictory assertion; absence of case loading/storage/network notification; input/navigation reset; keyboard/mobile and real-browser behavior. Those are future tests, not current passes.

## Scope boundaries

No implementation files changed. This review performed no external communication, publication, merge, deployment or database action. Subsequent preservation of these research documents in a draft PR does not change the design-only disposition. This review recommends a **design-only outcome now**, with a narrower optional evidence-gap UI only after its value and exact scope are accepted. The original W19 automatic classification/notification-obligation feature remains unfinished.

## Follow-up consistency check

Re-read the appended “独立预审后的未决修正（优先于上述候选模型）” and the expert brief's four counterexamples. They consistently incorporate P1–P4 and preserve the design-only stop. The earlier single-event constraints and candidate pipeline are superseded research proposals, **not an implementation contract**. The added sequence/branch/truth-table questions remain unresolved and must not be reported as fixed code, expert approval, or completed W19 functionality. No further blocking inconsistency found in this documentation-only disposition; runtime and legal acceptance remain not performed.
