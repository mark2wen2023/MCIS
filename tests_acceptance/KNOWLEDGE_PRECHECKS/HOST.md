# Existing new-card source hostname validation fix

Actual main 3aba2bf isolated copy, no dependency on PR74/preview work. Existing POST /knowledge/cards
accepted five invalid hosts and wrote candidate/audit/snapshot rows: exa%mple.com, .example.com,
example..com, -example.com, example-.com. Five desired-refusal HTTP tests failed before patch (201).

Minimal runtime change: validate_new_source_host called only after existing validate_content in create,
before any transaction/write. Domain syntax checked via built-in IDNA encoding + bounded DNS labels;
existing globally-addressable IPv4 validation remains. No new endpoint, fetch or identity handling.
Historical content validator deliberately unchanged so legacy archives remain readable; old malformed
URL remains untrusted historical data, not repaired/published silently. A temporary-DB legacy row test
runs actual export+archive save and confirms a new identical invalid request is rejected.

New tests cover no-state-change rejection, ordinary/trailing-dot/IDN/global-IPv4 acceptance, and existing
private/local address rejection. Standard IPv6 literal was already rejected by existing dot-in-host
policy and remains rejected; this patch does not broaden accepted host families or claim IPv6 support.
IDNA here is Python built-in codec, not a general browser-URL equivalence or DNS/SSRF safety guarantee.

No DNS, network verification or authority check. Syntactic acceptance is not genuine publisher,
public status, permission, approved evidence or safe URL fetching. Actual production authentication
remains absent. No archive format or source data changed; no merge/deployment/push in this task.

Separately, five multiline tests confirmed real LF/TAB and literal slash-n already preserve correctly;
there was no reproducible multiline-loss bug, and no change was made for it.

Independent review found 254-character DNS host without root dot incorrectly accepted by initial
patch; fixed normalized (no terminal root dot) maximum to253 and added253/254 cases with/without
root dot. Known inherited URL-policy gap: 127.0.0.1. can still pass as a domain. This patch is not an
SSRF defense and must not be used to authorize fetching; resolving/connecting needs separate policy.
