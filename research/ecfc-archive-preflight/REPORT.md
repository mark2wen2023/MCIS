# ECFC isolated preflight experiment

PR #42 read-only checked open/draft; requested continuation head 41e933b. Local existing service validators used, not freshly blob-verified as a complete checkout. No production files changed.

Added bounded strict UTF-8 JSON decoding (2 MiB, depth/node bounds, duplicate members, NaN/Infinity/overflow, lone-surrogate rejection), exact envelope/profile/case checks, and an adapter invoking the existing real Python document/event structure and digest validators before the earlier relationship prototype. The profile is experimental, NOT an allocated .mcase version.

11 unittest tests passed using the existing Python environment. Initial fixture had the wrong validation shape and was corrected before the final passing run. Negative hash/digest tests assert the actual PreviewError rather than an arbitrary exception.

Remaining limits: no real C# invocation or professional graph recalculation; only basic synthetic empty-graph fixture; receipts still use old relationship sketch rather than full production schema; validation errors not normalized; parse limits are experimental not negotiated production limits; evidence bytes, authenticity, archive ZIP/path handling, generation/replay, consistent export snapshot, DB/filesystem transactions, restore/re-export and UI remain unimplemented. A recomputed digest is not authenticity. The export guard must remain.

No installation, NuGet/.NET, browser attempt, network restore, merge or deployment. Saved as an experimental draft only. Recommended next steps: larger real-document synthetic fixtures, receipt schema and event source inventory.

## Independent review and publication notes
11 unittest cases independently rerun successfully. The imported ECFC router was compared with its remote blob at commit 41e933b; full dependency tree not verified. Standard-library unittest runner imports existing FastAPI/SQLAlchemy dependencies. No dependency installation.
Depth/node validation occurs after JSON parsing with a total byte cap; this is not streaming depth enforcement. Fixtures contain empty synthetic graphs, not realistic multi-node/multi-history evidence. Receipt schema, evidence bytes, replay isolation, atomic restore and concurrent export remain unverified. No production integration or export-guard change.
The test sibling import has been made location-relative for the repository layout. With existing service dependencies available, run from repository root: `PYTHONPATH=service python -m unittest discover -s research/ecfc-archive-preflight -v`.
