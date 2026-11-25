# W21 raw browser-artifact preflight, de9356a only

```sh
python3 -B archive_gate.py /path/to/original.tgz --archive-sha256 <sender-supplied-SHA-256>
python3 -B -m unittest -v
```

The exact package and independent outer SHA-256 have not been provided. The outer digest is required and must be obtained separately from the sender; calculating it from an unverified download does not supply an independent digest. This is not the earlier 215c057e package, and accepts neither its pins nor a reconstructed archive. No expected byte count or manifest name other than SHA256SUMS is assumed. Operational limits (32 MB compressed, 6 MB/member, 64 MB aggregate regular content, 96 entries) are safety limits, not delivery specifications.

The intake reads the gzip tar without extracting or executing anything. It checks the independent outer digest, source-provided report and JSONL digests, and original GNU-style SHA256SUMS entries against archive byte contents. It requires exactly 12 unique PNG basenames, all covered by the listing and with PNG signatures. It does not decode screenshots; dimensions and visual contents are not attested. File headers with traversal, absolute paths, links, non-regular members, duplicate paths or ambiguous member names are rejected. Additional JSON, JSONL, Markdown, text, PNG or log data is not run. The archive, report, listing and JSONL are never rewritten.

The receipt wire shape is derived from `scripts/verify-cross-repo-replay.mjs` (Git blob `798400226b3e4c6c69831e00001a18ff8b2cd149`, at `de9356a4616c0ef593ffff0ca81fd959ff24c1b3`). The fixed report/JSONL must agree on four orders of UTCs and exact 2D/3D offsets 100.000, 121.000, 124.250, 127.500 s, with explicit CPA false at the gap midpoint and raw vessel objects keyed by their synthetic IDs. Four referenced PNG names follow from the source and must be present among the 12; no other screenshot names are presumed. The raw receipt is not strict MCIS shape: it uses keyed vessel objects, not an ordered vessel list with the MCIS provenance/audit fields. No normalization or extra null fields are invented. A successful run establishes identity and raw artifact consistency, not that the 3D commit was independently checked out and run, that a browser was observed, or that the MCIS SQLite workflow passed.

An original-archive result is still pending. Eight standard-library test groups exercise a completely synthetic 12-PNG archive and independent failure cases including raw shape, exact milliseconds, wrong outer and inner hashes, missing SHA256SUMS and checksum entries, and unsafe member headers.
