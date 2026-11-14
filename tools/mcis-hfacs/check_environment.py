"""Offline prerequisite diagnosis; never builds or validates HFACS output."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess


def recipe():
    spec = importlib.util.spec_from_file_location('hfacs_build_recipe', Path(__file__).with_name('build.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check():
    build = recipe()
    dotnet = os.environ.get('MCIS_DOTNET', str(Path.home() / '.dotnet/dotnet'))
    result = {
        'contract': 'mcis-hfacs-environment/1',
        'expectedSdk': build.SDK,
        'selection': 'MCIS_DOTNET' if 'MCIS_DOTNET' in os.environ else 'HOME_DEFAULT',
        'dllPresent': (build.HERE / 'out/mcis-hfacs.dll').is_file(),
        'manifestPresent': (build.HERE / 'out/build-manifest.json').is_file(),
        'coreValidated': False,
    }
    def finish(status):
        return dict(result, status=status)
    if any(not (build.ROOT / path).is_file() for path in build.INPUTS):
        return finish('SOURCE_MISSING')
    # Match build.py selection exactly, including subprocess PATH resolution for
    # an explicitly configured bare executable name. Never silently fall back.
    try:
        proc = subprocess.run([dotnet, '--version'], capture_output=True, timeout=5, check=False)
    except FileNotFoundError:
        return finish('SDK_MISSING')
    except PermissionError:
        return finish('SDK_NOT_EXECUTABLE')
    except subprocess.TimeoutExpired:
        return finish('SDK_QUERY_TIMEOUT')
    except (OSError, ValueError):
        return finish('SDK_QUERY_FAILED')
    if proc.returncode:
        return finish('SDK_QUERY_FAILED')
    if proc.stdout.strip() != build.SDK.encode('ascii'):
        return finish('SDK_VERSION_MISMATCH')
    return finish('PREREQUISITES_READY')


if __name__ == '__main__':
    result = check()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['status'] == 'PREREQUISITES_READY' else 1)
