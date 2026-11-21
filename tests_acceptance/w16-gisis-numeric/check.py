"""AST-selected actual pure validator functions; no app, templates execution or export."""
import ast
import copy
from datetime import datetime
import math
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
OLD='94d5e38c926fda232bb987b60fa9145e4bcf01a7'
PATH='service/mcis_service/reports/gisis.py'
raw=subprocess.check_output(['git','show',OLD+':'+PATH],cwd=ROOT).decode() if '--old' in sys.argv else (ROOT/PATH).read_text()
tree=ast.parse(raw)
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('_valid_type','_invalid','validate_gisis')]
assert len(nodes)==3
namespace=dict(copy=copy,datetime=datetime,math=math,re=re,_MISSING='缺数据 / Missing data')
exec(compile(ast.Module(body=nodes,type_ignores=[]),PATH,'exec'),namespace)
# Extract existing literal rules only; never import service or execute templates.
templates=ast.parse((ROOT/'service/mcis_service/reports/templates.py').read_text())
fields=next(n.value for n in templates.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GISIS_FIELDS' for t in n.targets))
RULES={}
for call in fields.elts:
    name=ast.literal_eval(call.args[0])
    if name in ('latitude','longitude','grossTonnage'):
        RULES[name]={k.arg:ast.literal_eval(k.value) for k in call.keywords if k.arg in ('type','minimum','maximum')}

class Checks(unittest.TestCase):
    def check_value(self,name,value):
        doc={'fields':[dict(id=name,value=None,missing=True,required=True,rules=RULES[name],sourceRefs=['synthetic.'+name])]}
        before=copy.deepcopy(doc)
        result=namespace['validate_gisis'](doc,{name:value})
        self.assertEqual(doc,before)
        self.assertEqual(result['fields'][0]['value'],value)
        self.assertIn('request.values.',result['fields'][0]['sourceRefs'][0])
        return result

    def test_large_integer_latitude_longitude_get_range_error(self):
        for name in ('latitude','longitude'):
            for value in (10**400,-10**400):
                with self.subTest(name=name,sign=value>0):
                    result=self.check_value(name,value)
                    self.assertFalse(result['valid'])
                    self.assertEqual(result['errors'][0]['code'],'field_range')

    def test_unbounded_existing_numeric_rule_is_not_given_new_maximum(self):
        self.assertTrue(self.check_value('grossTonnage',10**400)['valid'])

    def test_zero_boundaries_bool_and_nonfinite_keep_existing_meaning(self):
        for name,limit in [('latitude',90),('longitude',180)]:
            for value in (0,0.0,limit,-limit):self.assertTrue(self.check_value(name,value)['valid'])
            for value in (True,False,float('inf'),float('-inf')):
                self.assertEqual(self.check_value(name,value)['errors'][0]['code'],'field_type')
        self.assertEqual(namespace['_invalid'](float('nan'),RULES['latitude'])[0],'field_type')

    def test_missing_remains_missing(self):
        for value in (None,'','  '):
            doc={'fields':[dict(id='latitude',value=value,missing=True,required=True,rules=RULES['latitude'],sourceRefs=['synthetic'])]}
            result=namespace['validate_gisis'](doc)
            self.assertEqual(result['errors'][0]['code'],'field_required')

if __name__=='__main__':
    unittest.main(argv=[sys.argv[0]],verbosity=2)
