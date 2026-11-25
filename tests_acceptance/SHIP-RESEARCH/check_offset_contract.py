"""在指定的只读 MCIS 源树上运行合成语义与坐标验收；返回实际检查结果。"""
import argparse
import json
import math
import sys
from pathlib import Path


def run(source):
    sys.path.insert(0, str(source.resolve() / 'service'))
    from mcis_service.agents.skills.ship_reconstruction.offset_cell_semantics import classify_cell
    from mcis_service.agents.skills.ship_reconstruction.coordinate_frame import normalize_offset

    checks = {}
    evidence = {'document_id': 'synthetic', 'locator': 'fixture-A'}

    def rejected(fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except ValueError:
            return True
        return False

    checks['blank_remains_unknown'] = classify_cell(None)['semantic'] == 'unknown'
    for semantic in ('not_applicable', 'outside_domain', 'omitted'):
        cell = classify_cell(None, semantic=semantic, evidence=evidence)
        checks[semantic] = cell['value'] is None and cell['evidence'] == evidence and cell['review'] == 'pending' and not cell['lofting_authorized']
    zero = classify_cell(0, semantic='confirmed_zero', evidence=evidence)
    checks['confirmed_zero'] = zero['value'] == 0 and zero['evidence'] == evidence
    for name, value, meaning, provenance in (
        ('no_blank_to_zero', None, 'confirmed_zero', evidence),
        ('no_zero_without_evidence', 0, 'confirmed_zero', None),
        ('nonzero_cannot_be_zero', 1, 'confirmed_zero', evidence),
        ('no_semantic_without_evidence', None, 'omitted', None),
    ):
        checks[name] = rejected(classify_cell, value, semantic=meaning, evidence=provenance)

    frame = dict(unit='mm', x_origin_m=2, z_origin_m=3, x_direction='aft', z_direction='down', source=evidence, review='accepted')
    mapped = normalize_offset(400, 200, 100, frame=frame)
    checks['scaled_reversed_axes'] = all(math.isclose(mapped[k], v) for k, v in [('station_x_m', 1.6), ('height_z_m', 2.8), ('half_breadth_m', .1)])
    checks['frame_provenance_and_gate'] = mapped['frame_source'] == evidence and mapped['research_only'] and not mapped['lofting_authorized']
    mapped = normalize_offset(1, 2, 3, frame={**frame, 'x_direction': 'forward', 'z_direction': 'up', 'unit': 'cm'})
    checks['positive_axes_cm'] = math.isclose(mapped['station_x_m'], 2.01) and math.isclose(mapped['height_z_m'], 3.02) and math.isclose(mapped['half_breadth_m'], .03)
    for field, value in [('review', 'pending'), ('unit','ft'), ('x_direction','unknown'), ('z_direction','unknown'), ('source', {})]:
        checks['reject_frame_' + field] = rejected(normalize_offset, 1, 1, 1, frame={**frame, field:value})
    for name, values in [('negative_breadth', (0, 0, -1)), ('infinite_station', (math.inf, 1, 1)), ('boolean_height', (1, True, 1))]:
        checks[name] = rejected(normalize_offset, *values, frame=frame)
    return checks


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source_tree', type=Path)
    results = run(parser.parse_args().source_tree)
    print(json.dumps(results, indent=2))
    raise SystemExit(0 if all(results.values()) else 1)
