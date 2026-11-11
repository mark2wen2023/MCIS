"""Compare independently executed before/after snapshots; never regenerates source data."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
before = json.loads((HERE / 'w14.3-current-before.json').read_text())
after = json.loads((HERE / 'w14.3-current-after.json').read_text())
changes = []
errors = []


def compare(a, b, path=''):
    if type(a) is not type(b):
        errors.append({'path': path, 'error': 'type changed'})
        return
    if isinstance(a, dict):
        if set(a) != set(b):
            errors.append({'path': path, 'error': 'keys changed'})
        for key in a.keys() & b.keys():
            compare(a[key], b[key], path + '/' + key)
    elif isinstance(a, list):
        if len(a) != len(b):
            errors.append({'path': path, 'error': 'length changed'})
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, path + '/' + str(i))
    elif a != b:
        item = {'path': path, 'before': a, 'after': b}
        if isinstance(a, (float, int)) and not isinstance(a, bool):
            item['delta'] = b - a
        changes.append(item)
        # Only clearance optimization output and its minimizer may move.
        if path.endswith('/MinClearanceM'):
            if abs(b - a) > 0.01:
                errors.append({'path': path, 'error': 'clearance difference exceeds 0.01 m'})
        elif path.endswith('/MinClearanceTimeSeconds') and '/rows/' in path:
            # Not collision time: collision TcSeconds and geometry remain exact below.
            if abs(b - a) > 0.001:
                errors.append({'path': path, 'error': 'minimizer shifted beyond optimizer time tolerance 0.001 s'})
        else:
            errors.append({'path': path, 'error': 'non-clearance result changed'})


compare(before, after)
report = {
    'method': 'Both snapshots execute actual Yangze22Case.Run; old and new source versions, same report inputs.',
    'scenario_clearance_tolerance_m': 0.01,
    'sensitivity_clearance_tolerance_m': 0.01,
    'minimizer_time_tolerance_s': 0.001,
    'collision_verdict_geometry_critical_display_exact': not any(
        e for e in errors if not e['path'].endswith(('/MinClearanceM', '/MinClearanceTimeSeconds'))),
    'nominal': [dict(id=a['ScenarioId'], before_m=a['MinClearanceM'], after_m=b['MinClearanceM'],
                     delta_m=b['MinClearanceM'] - a['MinClearanceM'],
                     before_time_s=a['MinClearanceTimeSeconds'], after_time_s=b['MinClearanceTimeSeconds'],
                     delta_time_s=b['MinClearanceTimeSeconds'] - a['MinClearanceTimeSeconds'])
                for a, b in zip(before['rows'], after['rows'])],
    'all_changed_fields': sorted(changes, key=lambda item: item['path']),
    'errors': errors, 'passed': not errors,
    'scope': 'W14.3 algorithm compatibility only. Existing W12 W14 export/seed retain their versioned source identity; not refreshed.',
}
(HERE / 'w14.3-current-comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'passed': report['passed'], 'changed_fields': len(changes), 'errors': errors,
                  'max_nominal_clearance_delta_m': max(abs(r['delta_m']) for r in report['nominal']),
                  'max_minimizer_time_delta_s': max(abs(r['delta_time_s']) for r in report['nominal'])}, ensure_ascii=False))
if errors:
    raise SystemExit(1)
