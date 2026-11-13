# Offline preview CLI (research adapter)

Run from this directory using Python 3:

```
python review_cli.py --candidates candidates.json --sources sources.json --output new-preview.html
python -m unittest -v
```

The source manifest must contain exactly `sources`, a list (maximum 16) of objects with exactly `sourceId`, `version`, `sourceType` (`Public` or `Synthetic`), `locator`, and `content`. These are explicit operator-provided snapshots, NOT authenticated provenance or facts. No file paths are resolved from manifest content, no remote requests are made. Candidate format remains the unchanged gate.py contract. Sources input has a 4 MiB encoded JSON budget; gate retains its tighter decoded-source and candidate budgets.

Validation and full HTML rendering occur before output creation. Output must be a new file; existing files and symlinks are refused. Exit codes: 0 generated; 4 domain/input rejection; 3 I/O failure; argparse usage errors 2. Error logs omit input paths/content. Source/candidate paths must open as regular files; FIFOs are rejected without waiting. Never use this to imply authenticity, approval, publication, or model quality.

Validation failures create no output. Storage errors during writing may leave an incomplete new file: exit 3 explicitly states output is unverified. Check storage and choose a new path; the tool will not overwrite or automatically delete files. Output is a local review artifact, not MCIS case persistence.

No production API/UI/identity/DB integration, real LLM call, browser visual acceptance, or deployment. Existing render/gate frozen files are not modified. Independent acceptance recorded separately.
