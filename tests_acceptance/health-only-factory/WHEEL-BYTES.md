# Official wheel byte verification — preparation only

On 2026-11-19, the developer downloaded the 11 wheels pinned by
`3cf0732ad33fb3bbac3a947c8128d4d2b613093e` from their exact official
`files.pythonhosted.org` URLs into a newly created temporary directory.
All 11 exact filenames, SHA-256 digests and byte sizes matched the manifest;
the directory contained exactly those 11 files. No redirect, fallback host,
installation, extraction, application import, HTTP application request, or
backend startup was performed. No wheel binaries are included in Git.

`wheel-byte-results.json` records each measured digest and size. The original
metadata manifest remains unchanged: its `wheel_bytes_downloaded: false`
describes that earlier metadata-only stage, not this subsequent observation.

`verify-wheel-bytes.py.txt` preserves the exact standard-library-only download
and verification script executed with:

```sh
python3 -I -S /tmp/verify-health-wheels.py tests_acceptance/health-only-factory/official-pypi-base-wheels.json
```

The temporary script was identical to the recorded `.txt` file. It pins the
manifest digest, rejects redirects, performs no retries, and stops on errors.
Reproduction requires separate permission for official file access and a new
controlled temporary directory; this record does not authorize any later stage.

Compatibility here means **filename tags**, checked against the observed
CPython 3.12.14 / Linux x86_64 / glibc 2.41 target: ten `py3-none-any` files and
one `cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64` file (glibc >=2.17).
Archive-internal tags/metadata were not examined; no contents were extracted.
This is not import, ABI execution, dependency-installation or runtime validation.

Only the previously verified base dependency set is covered. Future HTTP test
client/server dependencies remain unfrozen and untested. The trusted interpreter,
isolated import environment, installation and actual health HTTP behavior still
require separately reviewed verification. Full MCIS startup and archive tests
remain paused. These are developer observations, not independent acceptance.
