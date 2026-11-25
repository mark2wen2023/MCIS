"""Offline CAD intake. No network or automatic geometry inference."""
import hashlib
from pathlib import Path

def fingerprint(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def parse_drawing(path):
    path = Path(path)
    fmt = path.suffix.lower().lstrip('.')
    if fmt not in {'dwg', 'dxf', 'pdf'}:
        raise ValueError('unsupported format')
    digest = fingerprint(path)
    result = {'document': {'id': digest, 'sha256': digest, 'format': fmt,
                           'kind': 'unknown', 'status': 'unparsed'},
              'entities': [], 'issues': [], 'units': None}
    doc = result['document']
    if fmt != 'dxf':
        with path.open('rb') as stream:
            header = stream.read(6)
        if fmt == 'dwg' and not (header.startswith(b'AC10') and header[4:].isdigit()):
            doc['status'] = 'failed'
            result['issues'].append('invalid_or_unsupported_dwg_header')
        else:
            result['issues'].append('offline_dwg_conversion_required' if fmt == 'dwg' else 'pdf_adapter_required')
        return result
    try:
        import ezdxf
        cad = ezdxf.readfile(path)
        result['units'] = int(cad.header.get('$INSUNITS', 0)) or None
        for layout in cad.layouts:
            for entity in layout:
                kind = entity.dxftype()
                record = {'layout': layout.name, 'handle': entity.dxf.handle,
                          'layer': entity.dxf.layer, 'type': kind}
                if kind == 'TEXT':
                    record['text'] = entity.dxf.text
                elif kind == 'MTEXT':
                    record['text'] = entity.plain_text()
                elif kind == 'DIMENSION':
                    record['text'] = entity.dxf.text
                    record['measurement_raw'] = entity.get_measurement()
                    if not isinstance(record['measurement_raw'], (float, int)):
                        record['measurement_raw'] = list(record['measurement_raw'])
                result['entities'].append(record)
        doc['status'] = 'partial'
        result['issues'].append('semantic_extraction_and_block_expansion_pending')
        if result['units'] is None:
            result['issues'].append('drawing_units_unknown')
    except Exception as exc:
        doc['status'] = 'failed'
        result['entities'] = []
        result['issues'].append('dxf_read_failed:' + type(exc).__name__)
    return result
