# Caller and compatibility review (repository scope only)

Base1759643, reviewed before implementation. Legacy OpenAPI POST /cases/{caseId}/evidence
only described sha256 as required when content is absent. Legacy implementation computed
hash from content and ignored simultaneously provided sha256. No prior checksum-enforcement
promise is asserted.

Searched contentBase64 references and evidence POST calls across web/, tools/, unity/,
service/tests/ and tests_acceptance/. Concrete observations:
- web/src/evidenceIntake/EvidenceIntakePanel.tsx uses evidence-intakes:preview and :commit;
  its model sends contentBase64 and a requestDigest confirmation, not legacy dual SHA.
- web/src/pages/EvidencePage.tsx uses legacy reads and verify/access/patch actions, not
  a dual-field legacy creation request.
- tools/stage-demo/run.py creates evidence through the new Intake API. Its package import
  sourceSha256 is a different endpoint/contract and is unchanged.
- No contentBase64 old REST caller was found in Unity C# sources. Case-package/CustodyLedger
  domain SHA handling is unrelated and unchanged; this is not a Unity runtime test.
- Legacy creation test helpers generally use content-only or digest-only. One independent
  Base64 test intentionally sent all-zero SHA with valid bytes to document old precedence.
  It is a historical behavior test, not evidence of a deployed client depending on it.
  Updated that test to matching SHA under the NEW contract and added mismatch rejection
  assertions. Original committed report/test remain available at1759643.

No used repository client was found to break, so isolated implementation proceeded under
coordinator authorization. No deployment logs, telemetry, actual external clients or private
systems were inspected. Unknown external old clients sending placeholders/mismatches may
break; do not claim universal backward compatibility. Matching dual fields, content-only,
SHA-only, null-as-absent and valid empty-file cases remain compatible by regression tests.
