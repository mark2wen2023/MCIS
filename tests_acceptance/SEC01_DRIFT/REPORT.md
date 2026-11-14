# SEC01 offline drift follow-up (draft)

Scope: build-time review gate only. No import into application startup, no authentication
configuration change, no deployment. Base: PR72 d9de7ea1d251a662eeddd8cf2f409b31042c5eb6.
This check cannot make the existing caller-controlled identity trustworthy.

## Coverage

- Existing topology/classification gate remains unchanged.
- Nonempty application dependency overrides reject the audit; foreign override providers reject.
- Middleware order/class/config and supported callback bytecode are compared, unsupported
  values stop with `REQUIRES_REVIEW`. Already-built middleware stacks reject inspection.
- Route endpoint and compiled dependency callable bytecode are both recorded. Retaining
  module/qualified-name while changing the body no longer evades this comparison.
- Only 36 project source files are tracked: actual route/dep implementation files plus
  entrypoint, context, config, and the audit implementation. This is NOT all production
  files or a transitive import graph. Unrelated helper changes do not cause every build
  to require a manifest update, but their semantics are NOT verified.
- New/deleted tracked file or bytes change reports specific paths, not an unexplained
  whole-tree failure. Adding a route in a previously unknown module adds its source.
- Mounts/opaque ASGI apps require separate review and currently fail this audit, even if
  the topology inventory is classified. WebSocket endpoint/dependency callables are inspected.

## Environment and maintenance

Python 3.12 is required by the existing workflow. The manifest records major/minor version;
bytecode across Python versions is NOT portable. Bytecode excludes checkout paths/line tables.
A dependency upgrade that changes included third-party routes may also require a fresh review.
The main repository dependencies remain unpinned; a fresh install failing because of a
library change is a review-required result, NOT proof of a security regression or authorization.
No workflow auto-regenerates/blesses the manifest. A reviewer checks changed file names,
route/action classifications and positive/negative business tests, then explicitly updates
only the associated evidence. Hash updates alone never discharge authentication review.
The manifest, test and workflow are themselves reviewable code, not tamper-proof controls.
Branch protection / required checks are not configured by this change.

## Honest boundaries

A passing gate means only the inspected surface equals its reviewed snapshot. It does not
prove source classification correct, trusted identity, cross-case isolation or safe exports.
Closure cells, mutable globals, default values, transitive helper implementations, third-party
middleware implementation, already-compiled ASGI wrappers and runtime mutation after the
snapshot are not fully verified. A synthetic test intentionally demonstrates unchanged
fingerprint after closure data mutation. Those are unverified boundaries, not “secure passes”.
No external SSO is involved. External permission revocation after a final check remains
an unresolved execution/transmission race. No runtime authorization guarantee is made.

## Tests

Initial isolated suite: 37 passed (24 unchanged PR72 tests + 13 new cases).
These are deterministic offline/synthetic code checks, not real DeepSeek/case reasoning tests.
Independent review and remote CI status are recorded separately; not claimed here as passed.

Final local validation: 48/48 route+drift checks (11 independent) passed;
with unchanged W19/W19.2/knowledge archive tests: 154/154 passed.
See INDEPENDENT.md and logs. No production identity or model tests implied.
