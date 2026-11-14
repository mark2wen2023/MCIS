"""Offline display projection: quotation location is not evidential support."""
from copy import deepcopy
import hashlib
from research.expert_group.packet import _packet, load_packet, PACKET_SHA256
from research.expert_meeting.machine import strict, verify_snapshot, MeetingError

MAX_LOCATIONS = 32


def locate_quote(source, quote):
    """Exact Unicode-codepoint spans; no normalization or first-match inference."""
    if type(source) is not str or type(quote) is not str or not quote.strip():
        raise MeetingError('citation text')
    if len(source) > 12000 or len(quote) > 2000:
        raise MeetingError('citation budget')
    locations, count, offset = [], 0, 0
    while True:
        start = source.find(quote, offset)
        if start < 0: break
        count += 1
        if len(locations) < MAX_LOCATIONS:
            locations.append({'start': start, 'length': len(quote)})
        offset = start + 1  # Count overlapping matches too.
    if not count: raise MeetingError('citation mismatch')
    return {'offsetUnit': 'unicode_codepoints', 'locations': locations,
            'occurrenceCount': count, 'locationsTruncated': count > MAX_LOCATIONS,
            'locationStatus': 'unique_exact_match' if count == 1 else 'ambiguous_exact_matches',
            'semanticSupportVerified': False}


def citation_view(snapshot):
    """Replay the bounded meeting before projecting its declared review quotes.

    Never use this return value as a model prompt or provider/identity certificate.
    Untrusted text must be rendered as text by any later UI, never as HTML.
    """
    verified = verify_snapshot(snapshot)
    data = strict(snapshot)
    packet = _packet(load_packet())
    items = {item['itemId']: item for item in packet['items']}
    rows = []
    for round_ in data['state']['rounds']:
        for role, response in round_['responses'].items():
            for review in response['reviews']:
                item = items[review['itemId']]
                rows.append({
                    'round': round_['number'], 'roleId': role, 'itemId': item['itemId'],
                    'ticketId': response['ticketId'], 'reviewStatus': 'unverified',
                    'declaredResponseSource': response['source'],
                    'claim': {'kind': 'human_authored_test_claim_including_counterexamples',
                              'text': item['claim']},
                    'source': {'kind': 'frozen_report_excerpt_declaration',
                               'text': item['sourceText'], 'sha256': item['sourceSha256'],
                               'locator': deepcopy(item['sourceLocator']),
                               'publicnessVerified': False, 'locatorAuthenticated': False},
                    'fixedReportCitation': deepcopy(item['citation']),
                    'reviewerSelectedCitation': {'quote': review['quote'],
                                                **locate_quote(item['sourceText'], review['quote'])},
                    'declaredLabel': review['label'], 'rationale': review['rationale'],
                    'uncertainty': review['uncertainty'],
                    'semanticSupportVerified': False, 'factActivated': False,
                })
    return {'schemaVersion': 1, 'kind': 'offline_meeting_citation_projection',
            'snapshotSha256': hashlib.sha256(snapshot).hexdigest(),
            'packetSha256': PACKET_SHA256, 'meetingId': data['state']['meetingId'],
            'phase': verified['phase'], 'mode': verified['mode'],
            'rows': rows, 'sourceDocumentCount': 1,
            'sourceCountingMeaning': 'all_items_share_one_frozen_report_page',
            'comparison': [deepcopy(r['comparison']) for r in data['state']['rounds']],
            'authenticityVerified': False, 'modelExecutionVerified': False,
            'semanticSupportVerified': False, 'factActivated': False,
            'consensusComputed': False}
