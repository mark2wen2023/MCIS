# Independent trusted source-extraction Skill review

Scope: code-owned manifest, remote authorization/execution binding, saved working
execution profile v2 and inert archive history. No real model/API request, web
changes or commits performed by this independent subtask.

## Final evidence

`service/tests/test_pi_skill_independent.py`: **16/16 passed**, zero skips, 18.00s.
One existing Starlette TestClient deprecation warning.

Independent tests verify:
- a new trusted Skill release before a request blocks provider invocation;
- a release change during mocked provider execution rejects the returned output;
- a change between accepted completion and save denies the write;
- session revocation still denies save despite a valid Skill reference;
- mutations to returned disclosure/manifest/messages do not mutate host snapshots;
- external Skill fields in protocol envelopes are rejected before provider calls;
- tool-budget constant drift fails closed;
- unknown historical Skill references import/read as inert unverified claims
  without consulting or executing the current registry and without changing
  active records;
- v1 with an added Skill, v2 without a Skill, extra reference fields, malformed
  ID/version/digest are rejected;
- old v1 history remains v1 without an inferred Skill association.

Current manifest content digest:
`9a8b6a55aaf56f7c45243effb712cc3177e19cfc9984eff052f35e4017ab1dcf`

No blocking issue found in this reviewed backend scope. Authorization binds the
actual source/session/mode, complete manifest, prompts, tools and budgets.
Provider pre/post checks recalculate that approval scope; saving verifies the
server-retained snapshot rather than substituting a new release. Working profile
v2 records the reference, while archive supplement-v2 remains a history envelope.

This is a fixed engineering procedure, not an external plugin execution system,
professional certification, semantic-support validator or factual approval. The
manifest explicitly marks semanticSupportVerified=false; instructions about
approximation, subject attribution and causality do not prove model compliance.
Stored/imported digests are not signed proof of execution or authority. No UI,
production identity, CI, deployment or real inference accuracy is claimed here.
