// Test transport only. No wildcard same-case fallback and no write requests.
const suffixes = ['', '/evidence', '/custody:verify-chain', '/timeline',
  '/conflicts', '/tracks', '/access-policy', '/evidence/EV-001/custody'];
const allowed = new Set(['SYN-A', 'SYN-B'].flatMap(caseId =>
  suffixes.map(suffix => `/api/v1/cases/${caseId}${suffix}`)));
export function allowedRequest(url, method = 'GET') {
  return method === 'GET' && allowed.has(url);
}
