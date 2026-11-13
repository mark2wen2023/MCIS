"""Planning-only chain check, not production archive support."""
def validate_plan(current, history, receipts, validate_document, validate_event):
    def require(x):
        if not x: raise ValueError('invalid archive plan')
    require(type(history) is list and type(receipts) is list)
    require(len(history) <= 10000 and len(receipts) <= 10000)
    if not history:
        require(current is None and receipts == [])
        return
    previous = None
    requests = {}
    prev_hash = '0'*64
    for revision, item in enumerate(history, 1):
        validate_event(item)
        require(type(item['revision']) is int and item['revision'] == revision)
        validate_document(item['after'])
        require(item['before'] == previous and item['prevHash'] == prev_hash)
        require(item['requestId'] not in requests)
        requests[item['requestId']] = item
        previous, prev_hash = item['after'], item['hash']
    validate_document(current)
    require(current == previous)
    require(len(receipts) == len(requests))
    seen = set()
    for receipt in receipts:
        key = receipt['requestId']
        require(key in requests and key not in seen)
        seen.add(key)
        item = requests[key]
        require(receipt['document'] == item['after'])
        require(receipt['operator'] == item['operator'] and receipt['role'] == item['role'])
