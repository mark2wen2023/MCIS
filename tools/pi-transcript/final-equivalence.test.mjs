import test from 'node:test';import assert from 'node:assert/strict';
import {equivalentFinal as eq} from './final-equivalence.mjs';
test('strict structure permits presentation only',()=>{
 assert(eq('{"a":1,"b":"x\\ny"}',' { "b": "x\\ny", "a":1 } '));
 assert(eq('{"x":"a"}','{"x":"\\u0061"}'));
});
for(const [name,a,b] of [
 ['duplicate','{"a":1,"a":1}','{"a":1}'],['nested duplicate','{"x":{"a":1,"\\u0061":1}}','{"x":{"a":1}}'],
 ['float','{"x":1.0}','{"x":1}'],['exponent','{"x":1e0}','{"x":1}'],['negative zero','-0','0'],
 ['bool','true','1'],['string number','"1"','1'],['citation whitespace','"a b"','"ab"'],['array order','[1,2]','[2,1]'],
 ['extra','{"a":1,"b":2}','{"a":1}'],['overflow lexeme','1e999','1e998'],['trailing','{}x','{}'],['invalid same','{a:1}','{a:1}'],['deep','['.repeat(66)+'0'+']'.repeat(66),'0']
])test(name,()=>assert.equal(eq(a,b),false));
