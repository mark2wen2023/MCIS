# W18.4 project HFACS classification draft CLI

Run tools/mcis-hfacs/mcis-hfacs.sh with JSON stdin and no arguments. Existing
.NET SDK8.0.428/Python3 required; MCIS_DOTNET selects dotnet. Contract:
contracts/hfacs-draft-v1.md. No external calls or business-data persistence.

Actions: {"action":"taxonomy"} and {"action":"validate","draft":...}.
Taxonomy comes directly from HfacsMaTaxonomy.All; 32 categories,5 roots, original
names/codes/layer names, null parent for roots, isLeaf via ChildrenOf. This is
project-specific maritime-adapted taxonomy requiring expert review, not an
official universal classification standard. Category titles are not allegations.

Each validation uses a fresh HfacsAnalysis and original AddFinding. Root/group
and leaf categories accepted for ToBeVerified. All entries fixed Draft,
ToBeVerified,Investigator; evidence/ECFC arrays empty, ledger null. No Confirm or
Reject call. Unknown category/duplicate ID invalidates entire batch (no partial
result). Description/rationale/scope protocol constraints are adapter checks;
rationale meaning and description truth are not classified or verified by core.
Layer/category results do not establish causality, responsibility or facts.

The backend owns source metadata binding, transaction, saved-draft revision,
authorization and audit. AddFinding does not emit save audit. This tool neither
confirms nor persists drafts. No W11 source or adapter is referenced.

Explicit seven unchanged core/domain sources compile in isolated locked builds.
build-manifest.json records source/artifact hashes. Generated out/ is not for
publication. Protocol/core failures exit4, operational failures nonzero; build
failures can produce no JSON. Never treat absent output as successful validation.

Run synthetic tests: python tools/mcis-hfacs/test_cli.py with SDK environment.
Concurrent rebuild test invalidates adapter receipt; run while adapter idle.
