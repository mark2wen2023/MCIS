# Validation record
A fresh temporary directory contained only package/ and public-dependencies/ (the nine authorized fixed public-source exports), not previous task directories. Actual commands and exits are in validation.json.

- python -I -B package/check.py --dependencies public-dependencies : exit 0; original 3 tests, 2 downstream scenarios and 4 invalid-input rejections.
- python -I -B package/test_dependencies.py --dependencies public-dependencies : exit 0; 11 changed-blob/wrong-original-hash rejections.
- python -I -B package/check.py --repo no-repository : expected exit 1, FIXED_OBJECT_MISSING:receiver; no repository creation or fetch.

The successful path tested is explicit fixed-source export, not successful local Git-object access. --repo uses the same verification and test path after reads; successful Git-object mode remains to be run where all listed historical objects exist. No Git objects were fabricated for this test.

Runtime needs writable temporary storage for verified module materialization. First run under the read-only sandbox could not create a temporary directory; the scoped local-test execution with permitted temporary writes then passed. No production storage is used.

Self-test status only. Not registration, ECFC persistent readback, production or semantic approval. No blind-review answer files in the package. Origin repository guidance was read; this is a new research-only directory, with its own status/frozen hashes, per request to change only the new package.
