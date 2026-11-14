# EXPERTCITATIONHTML — local static review export

Dependency baseline checked 2026-11-14: remote main73fc800, PR81 headde4729d,
citation candidate5322d92. This branch adds one slice on5322d92; it does not claim
these research candidates merged into main. Original frozen modules unchanged.

`render(snapshot_bytes)` validates the original snapshot through citation_view;
it does not accept caller-supplied projection authenticity flags. Returns static
HTML with explicit phase, mode declarations, provenance digests, human-authored
claims (including counterexamples), fixed versus selected citations, occurrence
ambiguity and unresolved differences. Partial/absent opinions remain partial or
absent. All execution/semantic/identity/fact claims stay unverified. No model tool,
case endpoint, uploads, active external URLs, JavaScript, auto-refresh or form.

All dynamic data is HTML-escaped, including rationale, source, labels and locator.
URLs render as inert text. CSP denies all resources except inline fixed CSS;
no scripts, event handlers or externally loaded fonts/images are emitted. A local
HTML file can itself be edited: this is not a signed artifact or verifier of that
file. Regenerate from the validated snapshot to repeat the consistency check.
Copying metadata into static HTML is not independent source authentication.

Explicit local stdout export:
`python -m research.expert_meeting.citation_html --render-stdin < snapshot.json > review.html`

This command reads at most MAX_SNAPSHOT+1 bytes and emits no HTML on validation
failure (exit2 with generic diagnostic). It creates no files itself; explicit shell
redirection is the user's local operation. `--render-stdin` is required. No secrets
or network connection needed. Arbitrary official/private cases are not supported;
only the already frozen public test packet is bound by the snapshot protocol.

Validation: Python HTMLParser checks escaped untrusted strings and absence of
active tags/resource attributes; CLI subprocess tests prove explicit invocation
and rejected-snapshot output suppression. These are source/parser tests, NOT a
real-browser security/visual acceptance. Native browser not verified; earlier
sandbox launch limitations have not been bypassed. No server/deployment needed.
Readability/responsive layout/accessibility need supported browser/manual review.
Real DeepSeek remains0/HOLD; provider declarations are not execution evidence.
