# Internal pending-packet consistency precheck

map_packet(bytes) validates only MCIS public-report pending-packet v1 structure and cross-field
consistency. It reuses existing knowledge content validation/digest and archive strict JSON parsing.
Success retains original packet bytes, full source envelope and a content projection. Admission,
authorization, source-byte verification, independent page verification and persistence remain false.
No router, database writer, startup hook, trusted identity, source resolver or publication approval.

This is deliberately a narrow single-locator/single-excerpt pending format, not a generic importer.
Caller assertions, valid URLs, matching hashes and self-consistent invented metadata cannot prove
publisher authenticity, public status, usage rights or permission to ingest. Never feed the content
projection directly into an unauthenticated production endpoint. Production admission remains
blocked on trusted identity/scope and trusted source registration/authorization, atomic provenance
persistence, transaction uncertainty/idempotency and archive coverage.

No new dependency is needed beyond service/requirements.txt. From service with dependencies installed:
python -m pytest -q tests/test_pending_packet_mapping.py tests/test_pending_packet_mapping_independent.py

40 local tests passed, including a clean copied source tree using installed dependencies with Python
file/network guards. This is not a fresh dependency install, remote CI, production SSO or LLM test.
The fixture is a minimal single-page public report packet, not an authenticating trust anchor.
