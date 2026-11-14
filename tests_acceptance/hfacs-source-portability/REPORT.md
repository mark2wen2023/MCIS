# Portable HFACS test source integrity

Direct parent main73fc8002868d9c6894b5fce6d03f7db690291bf6. Isolated branch
fix/hfacs-source-portability. No dependency on other outstanding test candidates.

Original test_cli.py compares seven Unity source files to ../mcis-w144, which
is absent in this isolated environment. Its real CLI rebuild cannot presently
reach that comparison because SDK is also absent. The missing-directory cause
is source/filesystem evidence, not a newly executed successful C# reproduction.

Replaced that external comparison with fixed seven SHA256 constants copied from
the pre-existing committed tests_acceptance/W184/verified-impl-sha256.txt, all
matching current core bytes. The constants are not recomputed from candidate
source/receipt at runtime. Core receipt hashes must match those pins, actual
bytes must match pins, and all receipt-listed source bytes must match their
receipt hashes. Missing core entries/files and matching source+receipt tampering
fail. The existing loop checking receipt-listed sources remains, as do manifest
before/after equality and three concurrent genuine CLI result equalities. New
checks occur before manifest invalidation and after genuine concurrent rebuild.

Trust anchor is reviewed repository history. This is not a signed supply-chain
attestation or protection from an actor rewriting both tests and their trusted
history. Legitimate future changes to pinned core files require explicit review
and updating the approved baseline, never automatic regeneration to green tests.
Historical W184 results are provenance only, not today's core execution evidence.
Production source, build recipe, CLI wrapper, classification protocol and API are
unchanged. No skips, fake binaries or fabricated classifier results are added.

SDK-free tests:19 passed in0.07s (unit.txt). Temporary standalone source copy has
neither Git metadata nor sibling checkout; tests cover seven changed-source plus
recomputed-receipt failures, seven missing files, original-receipt tampering,
omitted receipt entry and adapter byte mismatch. Pins separately cross-checked
against W184 record. CLI file compiles as Python and its7 real tests collect;
collection does not execute or pass those tests. Independent review is separate.

Current SDK and historical sibling are absent (environment.json). Actual core
build, concurrency, protocol/taxonomy and the two HFACS archive workflows remain
unverified. No SDK installation/download, deployment, merge or remote push.
