// Shared by the real-browser waits and the offline predicate checks.
function matchingRequest(requests, baseline, caseId, operator) {
  const matches = requests.filter(r => Number.isSafeInteger(r.id) && r.id > baseline
    && r.url === '/api/v1/cases/' + caseId + '/evidence'
    && r.operator === encodeURIComponent(operator));
  return matches.length === 1 ? matches[0].id : null;
}
function fourMetrics(values, expected) {
  return values.length === 4 && values.every(value => value === expected);
}
