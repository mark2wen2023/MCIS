import { caseForLocation, navigationForCase } from '../src/caseContext'
const demo = 'CASE-2026-DEMO-LILY-MARY', real = 'CJK-2024-1230-YangZe22-VegaDream'
let count = 0
function equal(a: string, b: string) { if (a !== b) throw new Error(`${a} != ${b}`); count++ }
for (const route of ['report', 'colreg', 'analysis', 'evidence', 'recs']) {
  equal(caseForLocation('/' + route, '?case=' + real, demo), real)
  equal(caseForLocation('/' + route, '', demo), demo)
  equal(navigationForCase(route, real, demo), '/' + route + '?case=' + real)
  equal(navigationForCase(route, demo, demo), '/' + route)
}
for (const route of ['interview', 'sim', 'cases']) {
  equal(caseForLocation('/' + route, '?case=' + real, demo), demo)
  equal(navigationForCase(route, real, demo), '/' + route)
}
equal(caseForLocation('/report', '?case=', demo), demo)
equal(navigationForCase('report', 'case with spaces', demo), '/report?case=case%20with%20spaces')
console.log(`case context: ${count} assertions passed`)
