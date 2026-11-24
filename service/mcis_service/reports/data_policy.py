"""Existing report data classification only; no case loading or authorization."""

HAILI5_CASE_ID = 'CASE-2025-HAILI5-WANA17'
YANGZE22_CASE_ID = 'CJK-2024-1230-YangZe22-VegaDream'
REAL_CASE_IDS = {HAILI5_CASE_ID, YANGZE22_CASE_ID}


def is_fictional(case: dict) -> bool:
    return case.get('isFictionalDemo') is True and case['caseId'] not in REAL_CASE_IDS


def data_status(case: dict) -> str:
    return 'fictional' if is_fictional(case) else ('authorized-public' if case['caseId'] in REAL_CASE_IDS else 'pending-confirmation')


