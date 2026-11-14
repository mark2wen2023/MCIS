# EXPERTTRACE — offline cross-view provenance regression

Base PR87head99b44f0481c2711a164b5d055b0a8a0e68acf90c, parent main25b9df6.
Remote main and PR87 were checked at task start. Only tests/docs/evidence added;
no runtime, UI, provider, service, source packet or credential changes.

Ten tests join validated meeting->citation projection->human task->static HTML.
Completion/failed/unknown/absent second-round variants bind task to exact snapshot,
packet and source SHA, original fixed citation, current round role/ticket, selected
quote and uncertainty. Quote offsets match original text but remain ambiguous
and unverified. Old opinions never fill the current round's missing slots.

Prior unresolved differences persist even after later identical labels; all human
tasks remain pending. Self-consistent synthetic assertions of human identity and
approval do not authenticate the author or activate facts. Two internally valid
histories sharing the same meeting UUID have distinct exact-byte task bindings;
UUID alone is insufficient to restore annotations. Mutating a ticket is rejected
by all three consumers. These tests prove local data relationships only, not that
an adversary cannot forge a new self-consistent history. No signatures or trusted
identity exist, and semantic entailment remains unverified.

Synthetic remote-declared opinions are not actual provider calls. The fixed public
report packet is unchanged; source URL not accessed. Render tests inspect strings,
not actual browser behavior. No model capability, real human review or deployment
is claimed. DeepSeek0/HOLD; prior private-directory/static-HTML limits remain.

Run `PYTHONPATH=. service/.venv/bin/python -m pytest -q tests_acceptance/EXPERTTRACE`.
No Git history dependency, network, environment secrets or new package dependency.
