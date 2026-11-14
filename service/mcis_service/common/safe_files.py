"""Bounded read-only descriptor traversal; not an immutable-storage guarantee."""
import os
from pathlib import Path

class ReadBudgetExceeded(ValueError):
    pass


class SafeReadUnavailable(RuntimeError):
    pass


def read_regular_no_symlinks(path, limit):
    # Pin each parent directory: a prior is_symlink check plus leaf O_NOFOLLOW
    # alone leaves a parent-replacement race. Unsupported platforms fail closed.
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError('invalid read budget')
    import stat
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or not path.name:
        raise ValueError('absolute bounded source path required')
    if (not hasattr(os, 'O_DIRECTORY') or not hasattr(os, 'O_NOFOLLOW')
            or os.open not in os.supports_dir_fd):
        raise SafeReadUnavailable('safe descriptor-relative file reads unavailable')
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open(path.anchor, directory_flags)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, directory_flags, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0), dir_fd=parent)
    finally:
        os.close(parent)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode): raise ValueError('not regular file')
        chunks, remaining = [], limit + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 1024 * 1024))
            if not chunk: break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
    finally:
        os.close(fd)
    if len(raw) > limit: raise ReadBudgetExceeded('file budget')
    return raw

