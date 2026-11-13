# IQ-1 prototype follow-up
Fixed independent finding: old verification IDs must not satisfy a new verification round after MoreVerification or reopen.
17 unittest tests pass, including three new regression cases. History and prior discussion packets remain unchanged; current-round IDs reset without deleting events. Idempotent replay of MoreVerification does not reset subsequent new evidence.
Not independently revalidated yet. Only in-memory mechanics; no production authentication, persistence, concurrency locks, strict schemas or archives. Exact AgentService string check is a fixture guard, not an identity security boundary. Multiple hypotheses remain a design requirement and are not implemented here. No remote prototype commit, no merge/deploy.
