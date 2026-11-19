# Offline installation preparation — not startup acceptance

Base: `fd69678a37b39e38d93fedf89d57e1a4bbc5f210`.
Developer execution on 2026-11-19: a new temporary virtual environment was
created with `python3 -I -S -m venv --without-pip`. All 11 previously downloaded
official wheels were rechecked for exact set, filename tags, size and SHA-256
against the pinned manifest before installation. Archive member names were
inspected for startup hooks/path anomalies; no wheel module was executed.

An existing execution-environment pip 26.2.2 performed the installation into
the new environment using `--python`, `--isolated`, `--no-index`, `--no-deps`,
`--require-hashes`, `--no-compile`, `--no-cache-dir` and explicit local wheel
file URLs. No bootstrap pip/setuptools or unpinned package was installed in
the target. The installer used an isolated standard-library startup and a
single explicit tooling path. Child environment variables were limited to
PATH, LANG and a null pip config path. No system or user environment was modified.
The existing pip is tooling supplied by this environment, not an additional
official wheel whose provenance was verified in this work; its version and
RECORD digest are recorded, not represented as independent provenance proof.

Results (`offline-install-results.json`):

- Exactly 11 target distributions match the locked versions; all 18 active
  base dependency declarations are satisfied, evaluated from installed metadata
  with the installer's vendored requirements parser. Extras were not selected.
- 400 installed RECORD file hashes and recorded sizes verified. RECORD entries
  without hashes are listed explicitly. The site inventory contains 409 files
  with relative paths, sizes and measured hashes. Generated metadata such as
  direct_url.json may differ across temporary paths on reproduction.
- `include-system-site-packages = false`; isolated target Python metadata probe
  reports user site disabled and no external site-packages/dist-packages path.
  No .pth, editable link or site/user customization file found in target site.
  Standard library and interpreter remain shared with the execution environment;
  this is a virtual environment, not an OS sandbox or standalone runtime.
- No FastAPI/Starlette/Pydantic/MCIS module imported in the probe. Only standard
  library metadata/site inspection and installer tooling ran. No HTTP or service.
- The existing three-file source snapshot was separately rechecked against
  `source-snapshot.json`: exact three files, hashes and lengths unchanged. It was
  not copied into the venv, placed on its import path or imported.

Exact executed scripts are preserved as non-autoexecuting `.py.txt` records.
The invocation shape was (paths are placeholders for controlled local locations):

```sh
python3 -I -S /tmp/install-health-offline.py "$MANIFEST" "$VERIFIED_WHEEL_DIR"
python3 -I -S /tmp/check-health-offline.py "$NEW_INSTALL_ROOT" "$MANIFEST"
```

The first script creates and prints a fresh root, with wheels outside that root;
it never installs from an index. The second checks the resulting environment.
The first script expects the recorded existing pip tooling version and digest
record location; this is not proof of reproducibility on an arbitrary colleague's
machine. Reproduction must first verify interpreter/tooling and local inputs.
No application startup permission follows from these commands or records.

No venv, wheel, media, database or credential is committed. This is developer
installation/metadata evidence, pending independent review; not actual import,
health HTTP, full MCIS startup or archive acceptance. HTTP testing dependencies
remain unfrozen. Startup and archive pauses remain in force.
