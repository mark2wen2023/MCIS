"""Synthetic offline protocol evidence, never model capability evidence."""
import hashlib
import json
import pytest
from research.expert_group.packet import _packet, load_packet, GroupError
from research.expert_group.receipt import Receipt, write_new
from research.expert_meeting.machine import Meeting, verify_snapshot


def test_snapshot_digest_in_existing_metadata_receipt(tmp_path):
    meeting=Meeting()
    meeting.act({'type':'stop'})
    raw=meeting.export()
    write_new(tmp_path/'snapshot.json',raw)
    ledger=Receipt(tmp_path/'receipt.jsonl')
    try:
        ledger.append({'phase':'snapshot_written','groupRunId':meeting.snapshot()['meetingId'],
                       'outputDigest':hashlib.sha256(raw).hexdigest(),'status':'stopped_by_operator',
                       'providerRequests':0,'transportMocked':True})
    finally: ledger.close()
    row=json.loads((tmp_path/'receipt.jsonl').read_bytes())
    assert row['event']['outputDigest']==hashlib.sha256((tmp_path/'snapshot.json').read_bytes()).hexdigest()
    checked=verify_snapshot((tmp_path/'snapshot.json').read_bytes())
    assert checked['phase']=='stopped_by_operator' and checked['authenticityVerified'] is False
    assert row['event']['providerRequests']==0
    # No group completion envelope is fabricated for a meeting snapshot.
    assert not (tmp_path/'completion.json').exists()


def test_public_packet_pinned_and_no_answer_key():
    raw=load_packet();data=_packet(raw)
    assert len({item['sourceSha256'] for item in data['items']})==1
    assert all(item['sourceLocator']['pdfPage']==28 for item in data['items'])
    assert all(set(item)=={'itemId','claim','sourceText','sourceSha256','sourceLocator','citation'} for item in data['items'])
    with pytest.raises(GroupError,match='packet_pin_mismatch'): _packet(raw+b' ')
