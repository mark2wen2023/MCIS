"""Legacy read compatibility: no new practical file limit; not a memory budget."""
import sys
from ..common.context import problem
from ..common.safe_files import SafeReadUnavailable, read_regular_no_symlinks


def read_content(path):
    try:
        return read_regular_no_symlinks(path.absolute(), sys.maxsize)
    except FileNotFoundError:
        raise  # Caller retains its existing missing-file behavior.
    except SafeReadUnavailable as exc:
        raise problem(503, 'EVIDENCE_SAFE_READ_UNAVAILABLE', '此平台不支持安全文件读取') from exc
    except (OSError, ValueError) as exc:
        raise problem(409, 'EVIDENCE_UNSAFE_CONTENT', '证据文件无法安全读取') from exc
