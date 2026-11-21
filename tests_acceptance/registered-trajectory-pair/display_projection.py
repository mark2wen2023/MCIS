"""Offline synthetic host projection only. No authentication or HTTP interface.
Call only inside the existing committed-read callback. Never accept UI/model pins.
The injected validator is the fixed B consumer, not a browser-provided function.
"""
from copy import deepcopy


def project(record, *, validate_host_record):
    # Fail before constructing any display output. Existing validator checks every
    # pin against fixed raw bytes and both frames against the actual projector.
    validate_host_record(record)
    fields = ('vesselId', 'position', 'headingDeg', 'courseDeg', 'time',
              'courseUsedAsHeading', 'collisionAngle', 'locator', 'status')
    frames = []
    for source in record['frames']:
        vessels = []
        for row in source['vessels']:
            item = {key: deepcopy(row[key]) for key in fields}
            if row['status'] == 'declared_gap':
                item['gap'] = deepcopy(row['gap'])
            vessels.append(item)
        frames.append(dict(caseId=source['caseId'], alignedUtc=source['alignedUtc'],
                           vessels=vessels, authenticityVerified=False,
                           collisionDetermined=False))
    return dict(scope='synthetic-display-only', caseId=record['caseId'], frames=frames)
