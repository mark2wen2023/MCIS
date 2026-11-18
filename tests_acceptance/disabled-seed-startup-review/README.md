# Disabled-seed startup verification draft — DO NOT EXECUTE

Based on aa02d61bf2f1e8f1805531a2af2b1f0326f3b8a7. Both scripts are .txt and exit
immediately before imports. No application/test/script execution performed. No seed bodies opened.
Do not remove gates, rename scripts for execution, install dependencies or resume archive tests.

## Frozen evidence versus missing prerequisites

freeze.json records the actual interpreter binary SHA256 and version from pyvenv.cfg (not a
version invocation), plus exact hashes of both inventory files. dependency-metadata.tsv records
installed distribution names/versions/METADATA hashes and direct_url presence, without importing
packages or printing metadata bodies. This establishes local metadata, NOT trusted wheel origin,
installed payload integrity or a complete transitive lock. Missing payload/stdlib/native manifests
are explicitly null; execution must fail until reviewed and pinned, never accept null as wildcard.
The existing requirements.txt lower bounds are not a lockfile.

source-allowlist.tsv freezes six reviewed code-only files by SHA256. It is deliberately NOT a
complete executable import closure. It must not be expanded by globbing or by importing to discover
missing modules. Review remaining route/model dependencies individually before approving a complete
list. In particular seed_annotations still contains fictional annotations; it is not on this
non-case list. No source copy has been prepared. Copying only this list cannot start the application;
that is an unresolved review prerequisite, not permission to omit or substitute required modules.

## Proposed controlled environment

Use pinned interpreter -I -S -B with explicit reviewed paths, no user site, current checkout,
PYTHONPATH, editable paths or automatic site processing. Reject .pth/.egg-link/startup hooks,
editable direct_url metadata and unexpected bytecode; do not quietly delete them or bypass a
rejection. If installed dependencies cannot satisfy this, stop for a separately reviewed artifact
preparation plan. Freeze actual artifact provenance and hashes before using a new dependency tree.
Interpreter symlink is resolved in freeze.json; freeze stdlib/native runtime too before execution.

Inputs and new temporary output directory must be owner-controlled and have no concurrent writers.
Require exact file sets and hashes before first MCIS import; manifest schema/path validation comes
first. Hashes alone do not establish race freedom. No credentials, real data, seed JSON/PDF/images,
whole-checkout copies or hidden fallbacks to default database paths. No localhost server needed.

## Observation and expected effects

Observe every Python import event (name/source), file-open path/mode, compile filename and exec
code filename from hook installation onward; capture pre-hook modules and final origins separately.
Never log source text, constants, arbitrary arguments, environments or database contents.
Three seed module imports or opens of their source/bytecode are failed acceptance, not a reason to
retry with another loader. Ordinary observation does NOT prevent an omitted module being loaded.
The proposed audit hook is not an OS sandbox: native extensions/file mappings and pre-hook startup
are not fully covered. A complete file-access claim requires separately reviewed OS observation;
none is configured or authorized by this draft. Thus it cannot yet promise zero case-byte reads.

Only create_app with explicit seed_demo=False and fresh SQLite/data paths is proposed. Expected
writes: temporary directories, schema/table/index/trigger creation, SQLite DB/WAL/SHM. Existing
ORM registry includes HFACS tables; no HFACS business/core invocation is intended. Unexpected
process/network/data sources must be reported, not silently whitelisted. No route calls, report
creation, analysis loading, Seed annotations, browser, recovery or fault/permission probes.
No assertions of enabled-seed behavior, production identity, archive recovery or dynamic isolation.

## Review gates

Approve complete non-case closure without changing runtime semantics; resolve remaining annotation
literals; pin dependency artifacts and runtime manifests; approve concrete launcher/check ordering
and observation limits. Only then separately decide whether normal startup may execute with the
known possibility of discovering an unexpected data import. Static candidate is not execution
approval. Existing API changes are listed in ../seed-startup-import-isolation/REVIEW.md.
