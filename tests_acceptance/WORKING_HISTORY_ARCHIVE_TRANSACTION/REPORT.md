# Independent archive transaction review

Independent suite: `service/tests/test_working_archive_transaction.py`, **6/6 passed**, zero skipped, 4.57s, synthetic records only.

- Two actual threads restore the same package concurrently: exactly one new copy and one idempotent replay, one database row.
- An injected final guard failure rolls back the entire import.
- Direct SQL UPDATE and DELETE cannot rewrite imported history.
- A newly opened Database instance reads the historical copy and replays the import; session token is absent from package bytes.
- Session expiry during export's last direct epoch read prevents returning the package. This independently confirms terminal authorization reordering after the separate review discovered the analogous restore boundary.

The final sixth test was added after the larger regression collection began and is also reported separately. Freeze SHA256: `38ddad108639cf6724339c3c38ef436cd6056745b8ae0154d6f9ed84a4452f14` (`working_history_archive.py`).

No new UI, production authentication, external API, real model, merge or deployment is validated. Package checksum is integrity only, not authenticity; imported actor and source declarations remain unverified. This is supplemental proposal/review/citation history, excluding original media, full interviews and identities/permissions, not a complete case backup.
