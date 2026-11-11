import importlib.util
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / 'generate_seed_candidate.py'
spec = importlib.util.spec_from_file_location('candidate', FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_numeric_paths_and_boolean_exclusion():
    assert list(mod.numeric_leaves({'b': [True, 1, 2.5], 'a': False})) == [['/b/1', 1], ['/b/2', 2.5]]


def test_diff_detects_missing_keys_and_array_length():
    assert list(mod.differences({}, {'x': None})) == [{'path': '/x', 'before': None, 'after': None}]
    assert list(mod.differences([1], [1, 2])) == [{'path': '', 'beforeLength': 1, 'afterLength': 2}]


def test_diff_numeric_change_is_not_metadata():
    assert list(mod.differences({'n': 1}, {'n': 2})) == [{'path': '/n', 'before': 1, 'after': 2}]
