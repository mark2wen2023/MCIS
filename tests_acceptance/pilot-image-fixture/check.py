"""Only pure fabricated bytes and source AST. NEVER execute prepare.py."""
import ast
import base64
import binascii
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import runpy
import struct
import subprocess
import unittest
import zlib
ROOT=Path(__file__).resolve().parents[2]
BASE='5ab815fd4e4386bbd716d7f092a5ccb903368827'
fixture=runpy.run_path(str(ROOT/'tools/pilot_image_acceptance/fixtures.py'))
def source(path):return subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True)
class Error(Exception):pass
scope=dict(base64=base64,binascii=binascii,hashlib=hashlib,json=json,re=re,datetime=datetime,math=math,problem=lambda *args:Error(args))
for path in ['service/mcis_service/evidence_intake/parser.py','service/mcis_service/image_review/contract.py']:
    tree=ast.parse(source(path));tree.body=[n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))]
    exec(compile(tree,'<pure parser AST>','exec'),scope)
class Checks(unittest.TestCase):
    def test_actual_candidate_parser_and_intake_inputs(self):
        materials=fixture['materials']();bodies=fixture['intake_bodies']()
        self.assertEqual(materials,fixture['materials']())
        candidate=scope['parse'](materials['candidate'][1])
        for kind,key in [('pdf','pdf_sha256'),('image','image_sha256'),('raw','raw_sha256')]:
            self.assertEqual(candidate['source'][key],hashlib.sha256(materials[kind][1]).hexdigest())
        self.assertEqual(candidate['recognizer']['pipeline'],'synthetic-not-executed')
        for kind,body in bodies.items():
            metadata,raw=scope['inputs'](body)
            self.assertEqual(raw,materials[kind][1]);self.assertEqual(metadata['confidentiality'],'Restricted')
        self.assertEqual(len(materials),4)

    def test_png_crc_pixels_and_pdf_offsets_no_decode(self):
        materials=fixture['materials']();png=materials['image'][1];self.assertEqual(png[:8],b'\x89PNG\r\n\x1a\n')
        pos=8;chunks={}
        while pos<len(png):
            size=struct.unpack('>I',png[pos:pos+4])[0];kind=png[pos+4:pos+8];data=png[pos+8:pos+8+size]
            self.assertEqual(struct.unpack('>I',png[pos+8+size:pos+12+size])[0],zlib.crc32(kind+data)&0xffffffff)
            chunks[kind]=data;pos+=12+size
        self.assertEqual(struct.unpack('>IIBBBBB',chunks[b'IHDR']),(8,8,8,2,0,0,0))
        self.assertEqual(zlib.decompress(chunks[b'IDAT']),(b'\x00'+b'\x00\x00\xff'*8)*8)
        pdf=materials['pdf'][1];offset=int(pdf.split(b'startxref\n')[1].splitlines()[0]);self.assertEqual(pdf[offset:offset+4],b'xref')
        entries=pdf[offset:].splitlines()[3:7]
        for i,entry in enumerate(entries,1):self.assertTrue(pdf[int(entry[:10]):].startswith(f'{i} 0 obj'.encode()))

    def test_case_schema_fields_and_explicit_synthetic_identity(self):
        schema=json.loads(source('contracts/schemas/case.schema.json'))
        docs=fixture['cases']();self.assertEqual([d['caseId'] for d in docs],['SYN-PILOT-A','SYN-PILOT-B'])
        for doc in docs:
            self.assertTrue(set(schema['required'])<=doc.keys());self.assertTrue(doc.keys()<=schema['properties'].keys())
            self.assertIs(doc['isFictionalDemo'],True);self.assertEqual(doc['incidentLocation'],{'lonDeg':0.0,'latDeg':0.0})
        # Field-shape check, NOT a complete JSON Schema execution claim.

    def test_browser_sequence_is_unexecuted_source_only(self):
        tree=ast.parse((ROOT/'tools/pilot_image_acceptance/browser_steps.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef))
        attrs=[n.func.attr for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertIn('reload',attrs);self.assertNotIn('launch',attrs);self.assertNotIn('add_cookies',attrs)
        self.assertNotIn('request',attrs)
        source=ast.unparse(fn)
        self.assertLess(source.index("get_by_text('导入已登记结果'"),source.index("for kind, digest"))
        self.assertIn("'sourceVerified': False",source)

    def test_unexecuted_orchestration_static_boundaries(self):
        tree=ast.parse((ROOT/'tools/pilot_image_acceptance/prepare.py').read_text())
        funcs={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        prep=funcs['prepare_registered_case_a'];text=ast.unparse(prep)
        self.assertIn('async with host.approved_scope()',text)
        self.assertLess(text.index('host.create_case'),text.index('/evidence-intakes:preview'))
        self.assertLess(text.index('/evidence-intakes:preview'),text.index('/evidence-intakes:commit'))
        self.assertLess(text.index("'Preparation must not create an image run'"),text.index('host.review_in_same_origin_page'))
        self.assertNotIn('put_doc',text);self.assertNotIn('INSERT',text)
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in ('session','execute','add','commit') for n in ast.walk(prep)))
        self.assertFalse(any(isinstance(n,(ast.Try,ast.While)) for n in ast.walk(prep)))
        bind=ast.unparse(funcs['bind_existing_case_creator'])
        self.assertIn('_register_basic_cases(APIRouter())',bind);self.assertIn('create_case(body=body, ctx=ctx)',bind)
        self.assertIn("context_for_creation(body['caseId'], 'case.create')",bind)
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='Ctx' for n in ast.walk(tree)))
        main=tree.body[-1];self.assertIsInstance(main,ast.If);self.assertIsInstance(main.body[0],ast.Raise)
        original=ast.parse(source('service/mcis_service/cases/basic_registration.py'))
        create=next(n for n in ast.walk(original) if isinstance(n,ast.FunctionDef) and n.name=='create_case')
        code=ast.unparse(create)
        for required in ['contracts.validate', 'ctx.role', 'CASE_EXISTS', 'put_doc', 'audit.append']:self.assertIn(required,code)
        self.assertNotIn('seed',code)

if __name__=='__main__':unittest.main()
