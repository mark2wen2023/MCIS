import test from 'node:test';import assert from 'node:assert/strict';import {finalDiagnostic as classify} from './final-diagnostic.mjs';
const same='{"quote":"a b\\nc","n":12}';
test('exact string only allows proceed',()=>assert.equal(classify(same,same),null));
test('absence of validation is not formatting',()=>assert.equal(classify(same,null),'MCIS_FINAL_UNVALIDATED_NO_VALIDATION'));
test('outer whitespace categorized but never accepted',()=>assert.equal(classify(' { "quote" : "a b\\nc", "n" : 12 } ',same),'MCIS_FINAL_UNVALIDATED_FORMATTING'));
for(const [name,value] of [['quote space','{"quote":"ab\\nc","n":12}'],['quote newline','{"quote":"a b c","n":12}'],['number','{"quote":"a b\\nc","n":13}'],['duplicate','{"quote":"bad","quote":"a b\\nc","n":12}'],['numeric whitespace','{"quote":"a b\\nc","n":1 2}'],['markdown','```json\n'+same+'\n```'],['unicode escape','{"quote":"a\\u0020b\\nc","n":12}']])test(name+' is changed, not just formatting',()=>assert.equal(classify(value,same),'MCIS_FINAL_UNVALIDATED_CHANGED'));
