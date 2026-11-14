# Legacy evidence content and package source reads (local candidate)

Depends on the three-file safe-read prerequisite, commit cb04aa68d705bd77b04aaa19777395dd75f3fb51.
Both evidence GET and legacy package build_files use descriptor-relative no-symlink reads.
Regular files retain exact bytes and actual-byte digest generation. Existing expected-hash
comparison remains in explicit verify operations; this candidate introduces no new mismatch gate.
Missing GET remains404 NO_CONTENT; missing legacy package blobs remain omitted.
Unsafe/special files return409 EVIDENCE_UNSAFE_CONTENT; unavailable platform support returns503
EVIDENCE_SAFE_READ_UNAVAILABLE. Failure creates no successful Access/export audit.
Public/denied role gates remain before content reads. Existing archival paths retain their gates.

The reader loop uses at most1MiB per os.read to permit the legacy sys.maxsize ceiling without
requesting an oversized allocation. This is NOT an aggregate memory budget: both old and new
paths assemble bytes in memory. No new8/16/32MiB cutoff is imposed on old legal files.
POSIX O_DIRECTORY/O_NOFOLLOW and dir_fd are required; unsupported platforms fail closed.
Synthetic local race tests do not establish a remote file-mutation capability. Pinned descriptors
do not freeze inode contents or protect writes, mounts/hardlinks, or all other read paths.
