# Case creation transaction prerequisite

A deterministic concurrent same-caseId API test reproduced the old create route's
check-then-insert race as an uncaught SQLAlchemy UNIQUE constraint IntegrityError.
No successful overwrite or loss of evidence was established by this reproduction.

The route now holds the existing process-local WRITE_LOCK through database commit
and begins SQLite BEGIN IMMEDIATE before its duplicate check. A competing same-ID
create observes the committed case and returns the existing CASE_EXISTS409 rather
than racing the insertion. Existing role check, schema, response and unique index
remain unchanged. The case and its audit entry remain in the same transaction.

This is a prerequisite for later local-incarnation allocation. It does not add a
generation token, migrate old cases, activate restored evidence, implement trusted
run persistence or review, or alter package import. SQLite writer reservation and
process-local locking are not a claim of portable distributed locking, indefinite
availability under external lock contention, or filesystem/crash atomicity.

Independent code review plus8 focused tests pass (primary1 and independent7).
Final21 API/SQLite regression tests pass, zero skips, including existing package
and restore boundary tests; counts overlap. Four simultaneous same-ID creates
produce one201 and three409 with one case/create audit. Four unauthorized roles
remain403/no writes. Injected failures after audit append and at commit roll back
both case and audit; fresh retry succeeds. No real browser/core/LLM/CI validation.
