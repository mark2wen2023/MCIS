"""Conservative ZIP byte-delivery gate; no decompression or trust in file labels."""
import io
import zipfile
from ..reports.access import require_content


def protect_container(session, case_id, role, raw):
    # ZIP end-record detection is bounded by zipfile and does not read any members.
    # Leading PK also covers truncated/corrupt ZIP copies instead of downgrading them.
    if raw.startswith(b'PK') or zipfile.is_zipfile(io.BytesIO(raw)):
        require_content(session, case_id, role)
