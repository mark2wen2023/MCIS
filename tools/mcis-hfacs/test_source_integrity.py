"""SDK-free source-integrity tests; no C# or classification success is implied."""
import hashlib
import importlib.util
from pathlib import Path
import shutil

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('hfacs_source_integrity', HERE / 'hfacs_source_integrity.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


@pytest.fixture
def isolated(tmp_path):
    root = tmp_path / 'standalone'
    for name in check.CORE_SHA256:
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    return root, dict(check.CORE_SHA256)


def test_pins_match_historical_acceptance_record():
    entries = {}
    for line in (ROOT / 'tests_acceptance/W184/verified-impl-sha256.txt').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if name.startswith('unity/'):
            entries[name] = digest
    assert len(entries) == 7
    assert check.CORE_SHA256 == entries
    check.verify_sources(ROOT, entries)


def test_standalone_without_git_sdk_or_sibling(isolated):
    root, inputs = isolated
    assert not (root / '.git').exists()
    assert not (root.parent / 'mcis-w144').exists()
    check.verify_sources(root, inputs)


@pytest.mark.parametrize('name', list(check.CORE_SHA256))
def test_changed_core_even_with_matching_recomputed_receipt_fails(isolated, name):
    root, inputs = isolated
    (root / name).write_bytes(b'changed source')
    inputs[name] = hashlib.sha256(b'changed source').hexdigest()
    with pytest.raises(AssertionError, match='Core receipt differs'):
        check.verify_sources(root, inputs)


@pytest.mark.parametrize('name', list(check.CORE_SHA256))
def test_missing_core_fails(isolated, name):
    root, inputs = isolated
    (root / name).unlink()
    with pytest.raises(FileNotFoundError):
        check.verify_sources(root, inputs)


def test_changed_source_original_receipt_fails(isolated):
    root, inputs = isolated
    (root / next(iter(inputs))).write_bytes(b'changed')
    with pytest.raises(AssertionError, match='Core source differs'):
        check.verify_sources(root, inputs)


def test_omitted_receipt_source_fails(isolated):
    root, inputs = isolated
    inputs.pop(next(iter(inputs)))
    with pytest.raises(AssertionError, match='omits'):
        check.verify_sources(root, inputs)


def test_adapter_source_still_checked(isolated):
    root, inputs = isolated
    (root / 'adapter.cs').write_bytes(b'original')
    inputs['adapter.cs'] = hashlib.sha256(b'original').hexdigest()
    check.verify_sources(root, inputs)
    (root / 'adapter.cs').write_bytes(b'changed')
    with pytest.raises(AssertionError, match='Receipt/source mismatch'):
        check.verify_sources(root, inputs)
