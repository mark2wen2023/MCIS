# Host-owned validated-reference completion

Opt-in trusted completion_mode=validated-reference is included in disclosure
and its approval digest. Default exact mode stays exact. No mode inference from
model content and no extra model tools. The sole accepted terminal text is
MCIS_COMPLETE_VALIDATED_PROPOSAL, byte-for-byte, without quotes or other text.

The marker carries no proposal and grants no authority. Node requires a current
successful validation within its run; Python independently checks its canonical
model terminal, pending call state, source read, unchanged scope/session/source,
deadline and latest successful validated candidate. Each validation attempt
clears the prior candidate before execution, including invalid/exception paths.
Python finishes its own retained original JSON, not model-supplied final text.
Only after successful finish does its accepted-content snapshot become available
to the in-process working host. The latter still re-parses and checks citations
inside the authorized working-store transaction. No final content is mixed in.

Exact mode rejects marker and reference mode rejects JSON/text/whitespace changes.
The reference mode applies only to the explicit working public probe for now.
Completion mode is retained in result/execution metadata. Browser/production UI,
archives, human judgment and activated facts remain outside this slice.

Historical f3ecba87 rejected final and be93095b exact-mode read-only acceptance
remain unchanged. No earlier unknown request is automatically retried.

## Verification and independent live result
Independent reference tests: Python12/12, Node8/8; mock full-probe cleanup4/4,
all zero skipped. Final Node suite87/87. Related Python suite85/85 zero skipped,
39.64s, includes prior remote/working tests and6 primary reference tests. These
counts overlap historical evidence; they are local tests, not CI.

New explicitly authorized run00975fc8-2298-4132-add3-a323c55989c2 succeeded:
actual Pi1.5.2 + official DeepSeek configured deepseek-v4-pro,3 real model requests,
2 real tools (read_transcript_excerpt, validate_extraction_proposal),7 proposals,
7 citations. Same server-owned accepted candidate was saved to working SQLite,
identical operation replay verified, database reopened for protected read,
scripted needs_verification review appended, and reopened again to verify both
unchanged original candidate and revision1. workingRehearsalVerified=true.
The recovery receipt records working_review_verified then accepted_pending_review.

This is a real model/tool/working-persistence **test** on one fixed authorized
public report excerpt (Shanghai MSA YANGZE22, printedpage1/PDFpage3; SHA256
c158ad790b5605dc4eea9303f9dc3748bb9f5ce07b969fd10f30cee9d6c45748).
The review actor is scripted_test_not_human; no actual investigator approved a
claim. Fact activation remains false. The temporary SQLite fixture was removed
before the final success response; it is not a permanent user case database.
No production login, browser UI, archive support, whole-case accuracy, CI,
merge or deployment is claimed. Earlier failed and unknown runs remain recorded.
