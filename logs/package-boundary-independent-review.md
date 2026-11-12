# Independent review: package ZIP boundary

Implementation reviewed: `service/mcis_service/package/mcase.py` SHA256 `ac68422554d2f40dec035f794a31db41c778fe51f17d2b4bbe892c7c157829d4`.
Spec: `contracts/W8-package-zip-boundary.md`. Three-entry freeze check passed before review. No implementation/self-test/shared ROADMAP files edited.

## Initial result: return for repair

Independent tests: **58 passed**, then **3 added file-ancestor cases failed**. Original green log `logs/package-boundary-independent-tests.txt`; red evidence `logs/package-boundary-independent-ancestor-red.txt` retained. No full-project or deployed/Unity acceptance claimed.

### D01: ancestor file/directory collisions survive inventory validation

A synthetic manifest-valid package containing `raw/a` and `raw/a/b` (in either order) survives decoder validation but the real import route returns HTTP 500. The filesystem importer can write one blob before encountering the collision. A case-insensitive ancestor collision `raw/A` + `raw/a/b` is accepted with HTTP 201 on this Linux executor, despite the decoder using case-insensitive member uniqueness for Windows/Unity compatibility.

This belongs to the selected unambiguous-path decoder scope: these cannot represent an unambiguous portable filesystem tree, and can be rejected before reading contents without implementing atomic filesystem transactions. Proposed fix: after collecting all normalized keys, reject any file key that is an ancestor of another member, case-insensitively and independently of archive order. Preserve legitimate `raw/` directory plus descendants.

### Repeated directory compatibility

Repository C# `unity/Assets/_Project/Scripts/Data/CasePackage/ZipArchiveUtil.cs:20-35` enumerates only files and creates a ZIP entry once for each file. It does not emit directory entries, so rejecting repeated explicit directory entries does not break its normal output. Third-party archives with repeated directory entries are rejected as explicitly documented compatibility tightening; no need to relax within this slice.

## Coverage

- 44 HTTP cases across verify/import: corrupt CRC, malformed UTF-8 names, central/local-name disagreement, unsupported compression, encryption, NUL, truncation/non-ZIP, unsafe segments, duplicate/case/backslash collisions. All returned 422 BAD_PACKAGE with no case or blob files.
- Corrupted deflate/bzip2/lzma streams return controlled 422.
- Full member inventory validated before any content read, and archive handles closed on success/error.
- Four compression modes preserve bytes across 120 deterministic random payload checks inside four tests.
- Four minimal synthetic Unity-style packages import/export and re-verify successfully.
- Empty ZIP keeps prior missing-manifest integrity report behavior.
- Python dependency warning: Starlette TestClient httpx deprecation. No failures attributable to warning.

## Limits

Partial repository snapshot, not complete clean clone. No network deployment or external writes. Tests use only temporary synthetic data. This does not validate resource budgets, malicious JSON/manifest/document semantics, production authentication, cryptographic authenticity, symlinks, case identifiers, or atomic filesystem transactions. No browser, whole-service, full-C# or Unity-runtime claim.

## Final independent retest: accepted within stated scope

Implementation repaired to SHA256 `a291bced8b1ce96358e92f6056eff67e99bc3dd65d3766837218f6bb315a77d3`. The three-entry current freeze matches exactly; the initial freeze and red evidence remain preserved.

The original independent suite was rerun unchanged: **61 passed**, no failed/skipped, 7.05 seconds. Log: `logs/package-boundary-independent-retest.txt`. Independent suite SHA256 `a88a5ea069b5ef2e675b405d61dc0d486f7ea51abffe5d62b931d8ab6d249e53`.

D01 is closed for this slice. Reviewed repair collects every normalized non-directory file key and checks slash-delimited ancestors of every entry before any payload read. This is archive-order independent, case-insensitive, also covers explicit descendant directories, and does not confuse string prefixes (`raw/a` versus `raw/abc`) with ancestry. Existing legitimate directory-plus-child and round-trip cases remained green. No implementation changes were made by the independent reviewer.

This is acceptance only of the specified ZIP decoder boundary, not overall package import security or whole-project acceptance. All scope limits above remain.

## W8.2 integration independent recheck

Target base is `37bbeb2d8694a7ac3b267cf9a3c0bcad263b5d07`, tree `c080264accec49a382dd13507e56beab6220ef30`. Independently recomputed Git blob SHA1 (including Git blob header) for every available file in the supplied full remote tree. All **41** entries listed in `integration-changed.json` exactly match the new base. Overall **621 match**, **843 absent**, **3 differ**:

- `service/mcis_service/package/mcase.py`: intended implementation change in this slice.
- `tools/mcis-compat/out/mcis-compat.dll` and `.pdb`: local rebuilt execution artifacts, not matching repository versions. They must be excluded from publication. This is not a clean full clone claim.

Machine-readable audit: `logs/package-boundary-independent-base-check.json`, including all matched/missing paths and the three expected/actual blob hashes. No other present tracked-file drift was found. Added untracked test/report artifacts are outside the remote-tree comparison.

The current package freeze (3 entries) and W8.2 freeze (11 entries) both pass without mismatch. Package implementation and independent test hashes are unchanged from the final standalone acceptance above. Original independent suite rerun without edits: **61 passed**, no failed/skipped, 7.39 seconds, one existing TestClient deprecation warning. Log: `logs/package-boundary-independent-integrated.txt`.

The package ZIP-boundary acceptance remains valid on this integrated snapshot, conditional on publishing only the intended source/test/spec/report changes and excluding rebuilt compat outputs. Aggregate service/core/W8.2 HTTP/Web checks are being run by the coordinator and are not claimed as independent reviewer runs here. No shared ROADMAP, production source, or original tests were edited during integration review.
