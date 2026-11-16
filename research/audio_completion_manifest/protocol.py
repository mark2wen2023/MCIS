"""Pure proposed completion claims; no filesystem, database or execution authority."""
import hashlib
import json
import re


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def inspect(manifest, context):
    """Context must eventually come from trusted transaction/worker observations.
    Presently all inputs are untrusted research claims, never evidence of completion.
    """
    denied = {'consistent_claims': False, 'export_allowed': False, 'restore_ready': False,
              'retry_allowed': False, 'delete_allowed': False, 'historical_proof': False}
    try:
        def require(condition):
            if not condition:
                raise ValueError('incomplete or inconsistent completion claims')

        require(type(manifest) is dict and set(manifest) == {
            'schema', 'caseId', 'taskId', 'generationId', 'auditId', 'members'})
        require(manifest['schema'] == 'audio-job-completion/v1')
        require(type(context) is dict and set(context) == {
            'caseId', 'taskId', 'generationId', 'auditId', 'registration', 'exit',
            'writers', 'commit', 'manifestSha256', 'members'})
        for key in ('caseId', 'taskId', 'generationId', 'auditId'):
            require(type(manifest[key]) is str and 0 < len(manifest[key]) <= 128)
            require(manifest[key] == context[key])
        require(context['registration'] == 'new-protocol')
        require(context['exit'] == 'successful' and context['writers'] == 'confirmed-closed')
        require(context['commit'] == 'confirmed')
        require(type(manifest['members']) is list and 4 <= len(manifest['members']) <= 256)
        names = set()
        for member in manifest['members']:
            require(type(member) is dict and set(member) == {'path', 'kind', 'size', 'sha256'})
            path = member['path']
            require(type(path) is str and len(path) <= 512)
            require(all(re.fullmatch(r'[A-Za-z0-9_.-]+', p) and p not in ('.', '..') for p in path.split('/')))
            require(path not in names)
            names.add(path)
            require(path in ('source.wav', 'raw.json', 'worker.log', 'home') or path.startswith('home/'))
            require(type(member['size']) is int and 0 <= member['size'] <= 2**63 - 1)
            if member['kind'] == 'directory':
                require(path == 'home' or path.startswith('home/'))
                require(member['size'] == 0 and member['sha256'] is None)
            else:
                require(member['kind'] == 'file' and path != 'home')
                require(type(member['sha256']) is str and re.fullmatch('[a-f0-9]{64}', member['sha256']))
        by_path = {m['path']: m for m in manifest['members']}
        require({'source.wav', 'raw.json', 'worker.log', 'home'} <= names)
        for path in ('source.wav', 'raw.json', 'worker.log'):
            require(by_path[path]['kind'] == 'file')
        require(by_path['home']['kind'] == 'directory')
        for path in names:
            if '/' in path:
                parent = path.rsplit('/', 1)[0]
                require(parent in by_path and by_path[parent]['kind'] == 'directory')
        # Exact enumeration includes empty directories. No filename grants discard authority.
        require(context['members'] == manifest['members'])
        require(context['manifestSha256'] == hashlib.sha256(canonical(manifest)).hexdigest())
        return {**denied, 'consistent_claims': True, 'reason': 'claims-only-not-observed-proof'}
    except (ValueError, TypeError, KeyError, RecursionError):
        return {**denied, 'reason': 'unresolved-completion'}
