# Synthetic Access / ET0 postcondition trial

Research only. Two components, NOT a connected original-time pipeline.

## Reproduce
Use an already provisioned Python environment containing the service dependencies (SQLAlchemy, FastAPI, jsonschema and their existing dependencies). No install, model, HTTP server or network access occurs in the test.

```sh
python -I -B research/evidence-timeline-et0/read_gate_trial/check.py --repo /path/to/MCIS
```

The local repository must already contain every fixed object in pins.json; missing objects fail. Alternatively export exactly those paths and bytes to a dependency directory and use `--dependencies /path/to/export`. Every file is checked against its pinned Git blob before import. The dependency-export mode was executed here; the Git-object positive mode has not been executed for this trial. No dependencies or original fixtures are duplicated in this package.

## Observed scope
The actual db90fdf73de7bd26ba75819f0102fc03d0789faf intake functions register fixed synthetic vessel-b bytes in fresh temporary SQLite, then perform a single controlled download. Fixture preparation creates a synthetic case, default policy, original registration and its audit. These preparation writes are outside the measured read delta.

After the read, a new engine/connection observes exactly one additional Access custody row and its corresponding custody.access audit row. Other fixture tables and blob hashes are unchanged; both chains verify. The synthetic denied ExternalExpert role receives 403 and leaves all rows and blobs unchanged. Role context and request transport are test substitutes, not authenticated users or an HTTP/identity integration test.

Separately, the unchanged 8a2478f66b6a41c753e3b71c6e1d95d4bf76a82c host adapter and 31c2a896d1717a7876a416f7d8ca295fa41378b8 scoped comparator consume their existing synthetic clock fixture with empty review records and selections. Before and after the database read they return NO_REVIEW / undetermined, authorityVerified=false, saved=false, with no input or database mutation.

The registered V1 trajectory is NOT converted into ET0 source rows. Its embedded corrected status and correctionSeconds=12 are original content only, not proof of reviewed calibration. This is a postcondition control using separate fixtures, not a single end-to-end execution or proof of a production authority gate. No calibration approval storage exists in this temporary schema; zero approvals means none were performed, not that a real approval service was exercised. No publication, report save, model call or real identity is exercised.

## Remaining gate
A trusted product source must supply version-bound original identity/locator and reviewed calibration selection before real ET0 integration can be claimed. Successful Access, audit continuity and literal corrected labels cannot supply that authority. This trial does not implement that missing seam or change permissions, APIs, contracts, W20 or service code.

## Recorded run
Two tests, exit 0. result.json and tests.log are the actual captured run. SHA256SUMS covers this package except itself. Exact local command and environment are in execution.json; paths there document the run only and are not runtime dependencies.
