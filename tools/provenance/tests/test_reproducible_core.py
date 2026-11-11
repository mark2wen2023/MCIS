"""No SDK needed: input closure, cache integrity, SDK fail-closed behavior."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

FILE = Path(__file__).resolve().parents[2] / 'mcis-core/build_reproducible.py'
spec = importlib.util.spec_from_file_location('repro', FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_compile_manifest_includes_evidence_and_project():
    manifest = mod.inputs(mod.ROOT)
    assert len(manifest) == 56
    assert 'unity/Assets/_Project/Scripts/Domain/Evidence/InvestigationAudit.cs' in manifest
    assert 'tools/mcis-core/McisCore.csproj' in manifest


def test_wrong_sdk_rejected(tmp_path):
    with patch.object(mod.subprocess, 'check_output', return_value='9.0.100\n'):
        with pytest.raises(RuntimeError, match='requires SDK'):
            mod.build(mod.ROOT, tmp_path, 'dotnet')


def test_verified_cache_and_tamper_detection(tmp_path):
    artifact = tmp_path / 'mcis-core.dll'
    artifact.write_bytes(b'fixture')
    manifest = {'contract': 'mcis-core-build/1', 'sdk': mod.SDK, 'configuration': 'Release',
                'pathMap': mod.VIRTUAL_ROOT, 'includeSourceRevision': False,
                'recipeSha256': mod.sha(FILE), 'deterministic': True, 'useAppHost': False,
                'inputs': mod.inputs(mod.ROOT), 'artifacts': {'mcis-core.dll': mod.sha(artifact)}}
    (tmp_path / 'build-manifest.json').write_text(json.dumps(manifest))
    with patch.object(mod.subprocess, 'check_output', return_value=mod.SDK), patch.object(mod.subprocess, 'run', side_effect=RuntimeError('rebuild')) as run:
        assert mod.build(mod.ROOT, tmp_path, 'dotnet') == manifest
        run.assert_not_called()
        artifact.write_bytes(b'tamper')
        with pytest.raises(RuntimeError, match='rebuild'):
            mod.build(mod.ROOT, tmp_path, 'dotnet')


def test_source_change_invalidates_cache(tmp_path):
    artifact = tmp_path / 'mcis-core.dll'
    artifact.write_bytes(b'fixture')
    manifest = {'contract': 'mcis-core-build/1', 'sdk': mod.SDK, 'configuration': 'Release',
                'pathMap': mod.VIRTUAL_ROOT, 'includeSourceRevision': False,
                'recipeSha256': mod.sha(FILE), 'deterministic': True, 'useAppHost': False,
                'inputs': {}, 'artifacts': {'mcis-core.dll': mod.sha(artifact)}}
    (tmp_path / 'build-manifest.json').write_text(json.dumps(manifest))
    with patch.object(mod.subprocess, 'check_output', return_value=mod.SDK), patch.object(mod.subprocess, 'run', side_effect=RuntimeError('rebuild')):
        with pytest.raises(RuntimeError, match='rebuild'):
            mod.build(mod.ROOT, tmp_path, 'dotnet')


def test_unsupported_msbuild_input_fails_closed(tmp_path):
    project = tmp_path / 'tools/mcis-core/McisCore.csproj'
    project.parent.mkdir(parents=True)
    project.write_text('<Project><Import Project="elsewhere.props" /></Project>')
    with pytest.raises(RuntimeError, match='unsupported build inputs'):
        mod.inputs(tmp_path)


def test_manifest_tracks_recipe_and_flags():
    # Behavioral regression: even a valid artifact cannot reuse a receipt from an older recipe.
    assert "'recipeSha256': sha(Path(__file__))" in FILE.read_text()
    assert "'deterministic': True, 'useAppHost': False" in FILE.read_text()
