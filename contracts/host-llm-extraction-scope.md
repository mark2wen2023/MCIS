# LLM extraction scope and reuse audit

## Existing implementation found
`agents/model_client.py` already supports opt-in loopback OpenAI-compatible text completion with bounded response, no redirects, environment proxies or tool calls. `agents/extraction.py` builds mandatory-redacted interview prompts and validates structured statements, exact unique source quotations and UTF-16 spans. The W20 router has an extraction/review queue, with policy/source rechecks and audit events. These are existing mechanisms, not newly invented in this slice.

The legacy router is still hosted in a role-header application. It must NOT be advertised as protected by the newer session-authenticated trial host. Registry entries for other agents are declarations, not proof of implemented autonomous experts or agent loops. The present slice does not implement expert-group debate, pi orchestration, audiovisual perception, or live internal-network data integration.

## Chosen new boundary
An independent trusted-host extraction entry uses same-database current session/case authorization and actual interview loading instead of routing through old role headers. It binds complete record, policy, case incarnation/epoch and any registered original source snapshot before model invocation and rechecks after. It reuses prompt and citation validation rather than duplicating W20.

Default provider is disconnected: no hidden fake result or automatic network call. Explicit fixture execution is labeled fixture and is not real inference. An optional explicit local provider must revalidate its loopback endpoint at invocation. No external hosted API or credentials are introduced. Actual model/API accuracy is unverified unless separately tested with an authorized configured model.

Returned proposals remain PendingReview. Exact quotation matching proves textual anchoring only, not factual truth or whether an interpretation follows from that quote. Run checksums aid comparison but are neither a persistent audit log nor signed provenance. No automatic statement/journal write, official review decision or responsibility determination is permitted. The caller still needs a safe UI/human review and persistence integration before production use.

## Callable contract
`describe(db, settings, session_token, case_id, record_id)` returns only bindingDigest and sourceScope after current authorization. `run(..., expected_binding_digest, provider=None)` requires that digest, re-reads the actual stored record/policy and refuses changed bindings. An explicit `FixtureProvider(json_text)` exercises parsing/citation contracts only. An explicit `LocalProvider(ModelConfig(loopback_v1_url, configured_name))` may call the selected local endpoint; it never auto-discovers settings or reads credentials. The configured model name is a declaration, not verified server identity.

Provider invocation receives only the mandatory-redacted messages. Original interview data stays in the trusted host for quote/span validation. Default not_connected returns no proposals. Provider failure returns a fixed sanitized error, not raw response/prompt. After invocation, authorization, full record, policy, case incarnation/epoch and registered source bytes are checked again. Revocation cannot retract bytes already sent; changed state prevents releasing a proposal.

`sourceScope=interview_document_only` means no registered original source was bound. `registered_original_bytes` means a current registered original reference was verified, not that the interview was a faithful transcription of it. The fixture test attaching a source proves the reference/integrity mechanism, not real accident factual validity.

No network HTTP route or UI button is added here. This is a real authenticated host-callable path over stored interviews, awaiting integration into a user-facing review flow. Existing legacy review endpoints are not made safe merely by this new function.
