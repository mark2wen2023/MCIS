# Static wheel-to-install comparison; execution still blocked

Developer check on 2026-11-19, base
`bb981b0bc9faa6bfe14ddfe41092eefbc2db5326`.
No target package, application, HTTP handler or service was executed.

The pinned manifest digest and each of the eleven official wheel sizes and
SHA-256 values were rechecked. ZIP members were read as bytes without extracting
or executing them. Each ordinary member was mapped directly to the corresponding
site-packages path; duplicate names, traversal, symlinks, cross-wheel collisions
and unreviewed `.data` relocation cause an explicit stop. This exact set contains
no `.data` relocation. Actual installed files are compared directly with wheel
bytes, not merely against their installed RECORD.

Results in `wheel-installed-comparison.json`:

- 365 files are byte-for-byte equal to their official wheel members, including
  package source/native files and original metadata other than RECORD.
- 11 RECORD files are installer-rewritten: both hashes are recorded; they are
  explicitly **not** claimed identical to the wheel. Their installed hashes and
  file sizes were separately checked in the preceding installation record.
- 33 new metadata files: INSTALLER must contain `pip` plus newline, REQUESTED
  must be empty, direct_url.json must identify the exact local wheel and locked
  archive SHA-256. These are generated provenance assertions, not original wheel
  contents or independent installation provenance.
- Exact installed site file set: 409, with no unclassified additional files.
- 11 entries outside site-packages are explicitly unverified against wheels:
  venv configuration, activation files, Python links and generated `fastapi`/`idna`
  console scripts. None of these console scripts was executed. The base Python,
  standard library, loader and OS libraries are not covered by this comparison.

The exact static script is `compare-wheel-install.py.txt`. Invocation shape:

```sh
python3 -I -S /tmp/compare-wheel-install.py "$MANIFEST" "$WHEELS" "$VENV" "$RESULT_JSON"
```

It only reads local wheel/installed bytes and writes the requested JSON result.
Controlled stable directories are a precondition; this is not an adversarial
concurrent-filesystem isolation proof. No binaries or local absolute paths are
included in the result record.

## Isolation capability observation, not execution permission

Read-only executable/path metadata showed Docker, bwrap and unshare binaries;
a Docker socket path exists. No daemon connection, container/image listing,
namespace creation, permission probe or sandbox command was attempted. Tool
presence and socket permissions do not prove a supported, authorized sandbox
configuration, available trusted image, mount isolation or network isolation.
The current work environment exposes the checkout. A venv only separates Python
packages; it does not prevent access to that checkout, user directories or data.
No existing reviewed profile establishing the required no-repository/no-user-mount
execution boundary has been supplied or verified. **Startup remains blocked.**

Concrete next gate: obtain a platform-supported, approved empty execution profile
with no original checkout/user/credential mounts, disabled network and a pinned
trusted CPython/runtime image. Review its exact image digest and mount list before
starting it. Only then transfer the three hashed source files plus verified
package files, account explicitly for runtime/standard-library dependencies and
any required generated metadata, and recheck the destination inventory before
separately authorizing an import-only check. Do not copy the whole venv or its
unverified console launchers as a purported hermetic runtime. If the platform
cannot provide that profile, stop; do not substitute namespace/permission changes.

This record does not authorize imports, FastAPI/ASGI/HTTP execution, full MCIS
startup, archive tests, fault/permission probes or previously paused tests.
It is developer static evidence, pending independent review, not sandbox or
application acceptance.
