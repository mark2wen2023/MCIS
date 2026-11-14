# Human quote-check display improvement

The actual DeepSeek/Pi semantic run exposed qualifier-loss and missing-information interpretation risks. This slice does not change the model or claim to solve semantics automatically. Existing working/archive views retained quote data, but ordinary HTML blockquotes collapsed whitespace visually.

New shared SourceQuoteReview component renders the supplied quote unchanged using white-space:pre-wrap and distinguishes it from the AI summary/structured claim. It always reminds the reviewer to retain qualifiers, avoid treating blank or missing records as proof of presence/absence, consult the source page and other evidence, and separate exact location from semantic support. Preserved extracted whitespace does not reconstruct PDF table geometry. Historical quotations remain explicitly unverified archive declarations.

No normalization, trimming, inferred qualifier, semantic verdict, success mark, automatic write, RPC/schema/storage/route or authority change. No new model request and no repeat of prior real runs. Tests here are UI/safety tests, not synthetic evidence presented as model capability.

Implementation checks:5 new source-render cases, prior Pi working30, archive28, Skill26, strict TypeScript all passed. Independent new7 checks passed, including current/history actual component integration, escaped HTML-looking text, CR/LF/tabs/repeated spaces/Unicode, disconnected clearing, no automatic port calls or fetch, and retained script-review warnings. Coordinator reran new5+independent7 exit0 using explicit installed HappyDOM path; an initial attempt without that path failed to find the dependency, corrected without code changes. Counts overlap and are not additive unique coverage.

Native implementation and separate native independent UI reviewer, not separate Codex application sessions. HappyDOM verifies DOM text/style properties, not actual browser-engine rendering, visual layout, production mounting or PDF reconstruction. No CI/full-service regression, merge or deployment claim.

Independent disposition: no blocking issue, suitable for Draft submission. Independent rerun also covered prior working24+9 and archive27+13 cases and strict TypeScript. See tests_acceptance/SOURCE_QUOTE_UI/INDEPENDENT.md. Freeze:logs/source-quote-review-impl-hashes-frozen.txt.
