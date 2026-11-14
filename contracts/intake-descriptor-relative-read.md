# Stage-A prerequisite: descriptor-relative registered-original reading

This is a read-path hardening slice, NOT saved check runs, atomic storage or
human approval. Prior intake.file_path checks parent symlinks before read_file
opens the leaf with O_NOFOLLOW. A parent can change between those operations.

read_file now requires an absolute no-.. path and opens each directory component
relative to the preceding pinned descriptor with O_DIRECTORY/O_NOFOLLOW. The
leaf is opened relative to the last directory with O_NOFOLLOW/nonblocking; fstat
still requires a regular file, and reads remain bounded by MAX_BYTES+1. Parent
replacement after a directory opens does not redirect the read into a symlink
replacement. Opened descriptor chain is closed as traversal proceeds and on error.
Existing authorized receipt/hash/metadata and pre/post compute checks remain.

No filesystem permissions, files, links, credentials, writer paths, archive rules
or API grants are changed. The helper is used by the existing load_receipt path,
not a new arbitrary-file reader. Initial orphan existence checks and exclusive
write path are unchanged; writer races are NOT claimed fixed. External changes
to an opened file's bytes remain possible and are checked by existing hashes;
this does not give the future saved-run transaction a filesystem atomic lease.

## Platform boundary
Actual tests run on Linux/POSIX. O_DIRECTORY, O_NOFOLLOW and dir_fd support are
required; missing support returns explicit503 INTAKE_SAFE_READ_UNAVAILABLE with
no unsafe fallback. This does not claim Windows support or tested macOS behavior.
Directory opens may require read as well as search permission; execute-only
ancestor layouts can fail closed and need deployment-specific assessment, not
automatic chmod or privilege escalation. Configured blob root is resolved by
existing code; traversal never relaxes its source-relative path constraints.

## Initial tests
New test_intake_descriptor_read.py5 pass: regular/oversize, parent/leaf symlink,
directory swapped to external symlink after opening (still reads original), all
captured descriptors closed, unsupported-platform API503. These are real local
filesystem tests with controlled race injection, not a nondeterministic stress
proof or protected production storage guarantee. Regression/independent below.
No merge/deployment; stageA still blocked on its remaining lifecycle requirements.

Independent audit found a real directory-leaf fd leak in the first candidate:
os.fdopen could throw before acquiring ownership. That candidate was not published.
The final reader uses raw fd fstat + bounded os.read loop with unconditional
finally close, also covering read/stat failure. Independent9 plus primary5 now
pass14/14; actual Linux FIFO and deterministic parent-swap probes included.
A regression process started on the earlier candidate passed123 but is NOT used
as final-version validation; final full rerun is recorded below when complete.

Final independent64/64 pass, zero skips: new9, primary5 and50 existing permission,
path, registration/parent tests, actual W2 enabled. Unsupported-platform behavior
is capability simulation only; no Windows/macOS runtime verification. Existing
Starlette deprecation warning only. No product changes by reviewer.
Final implementer regression on corrected version:132/132 pass, zero skips,
covering new descriptor tests plus existing registered-preview, CSV differential,
timestamp and parent-report suites, actual W2 enabled. Counts overlap with64.
