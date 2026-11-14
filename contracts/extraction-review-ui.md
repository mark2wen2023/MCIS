# Ephemeral extraction proposal review UI

Standalone, non-production `ExtractionReview` and `createExtractionReviewPort`. Not mounted in legacy routes; no legacy role headers, fetch, tokens, storage, model environment configuration or implicit credentials. Trusted host supplies fixed context/case/record and provider outside this UI. Default component is disconnected; connected host with no provider returns `not_connected`, not fake proposals.

Generate and review requests carry explicit canonical UUID requestId. Unconfirmed result freezes the original request including decisions and ID for exact retry. No automatic new request. New explicit generation replaces old draft. A host rejection is conservatively unknown; unavailable/closed host may require a newly authorized context, not bypass/reinterpretation. Scope/port change or unmount clears state and ignores late replies. Layout cleanup prevents old source text surviving context paint. Failure hides proposals and reasons but preserves pending request privately in memory for exact retry.

Proposals expose summary, bounded structured claim, read-only quote and UTF-16 span. Explicit fixture is labelled fixed simulated output, never model inference. Local provider mode is not verified model identity. References mean unique exact quotation match, not source truth. Document-only vs registered original-byte scope is shown.

Each proposal requires adopted_working / rejected / needs_verification and nonblank reason <=1000. Quote and claims are not editable in review command. Host reauthorizes original binding; success must match current proposal and submitted decisions. Receipt is working-only, saved=false, factVerified=false. No durable review, production identity, evidence conclusion or responsibility decision.

This business-port contract is for trusted callback IPC; the test uses Node stdio, not a browser bridge. A production deployment still needs secure host lifecycle, authentication, durable audit/storage, end-user integration and real-model validation.
