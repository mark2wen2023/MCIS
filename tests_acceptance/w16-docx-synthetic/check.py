"""Real exporter -> temporary DOCX -> ZIP/XML readback; synthetic input only."""
from copy import deepcopy
from hashlib import sha256
import importlib.abc
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
# Freeze the complete first-party import closure, including package initializers.
PINS = {'service/mcis_service/__init__.py': '0af1ae7229694ada406cc87b5cbaaf195441620cb48e8dda54df83a3f6295480', 'service/mcis_service/config.py': '0e5e5262bcffe7f63fbca833e5cd267045d9db790d7600f0848c5451f21aa2ea', 'service/mcis_service/reports/__init__.py': '8ba52ec498ce30f3263c03c45f29c306d47ea2517d541d8c3e208cbf7f4d5020', 'service/mcis_service/reports/templates.py': '46304abd191be543146f56ba5789e7c36d18f4bb20ec81bb62e83dece2a31aa4', 'service/mcis_service/reports/exporter.py': '9124188c4c68d5473046fc2d149ae4a8cf244dcf91bbc9b40e57e666042088eb'}

class ImportBoundary(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        allowed = {'mcis_service', 'mcis_service.config', 'mcis_service.reports',
                   'mcis_service.reports.templates', 'mcis_service.reports.exporter'}
        if fullname.startswith('mcis_service') and fullname not in allowed:
            raise ImportError('Outside reviewed exporter closure')
        return None

for name, expected in PINS.items():
    if sha256((ROOT / name).read_bytes()).hexdigest() != expected:
        raise RuntimeError('Fixed source differs: ' + name)
sys.meta_path.insert(0, ImportBoundary())
sys.path.insert(0, str(ROOT / 'service'))
from mcis_service.reports.exporter import export_report

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def text(node):
    return ''.join(n.text or '' for n in node.iter(W + 't'))

class Checks(unittest.TestCase):
    def test_actual_bilingual_docx(self):
        sentences = [
            {'sentenceId':'syn-pending','status':'Draft','missing':True,
             'textZh':'待核：通联来源尚未提供。',
             'textEn':'Pending verification: communications source not provided.',
             'citations':[{'kind':'evidence','id':'SYN-MISSING','href':'#synthetic',
                           'registration':'missing','needsReview':True}]},
            {'sentenceId':'syn-zero','status':'Draft','missing':False,
             'textZh':'合成计数为 0；不代表已核实。',
             'textEn':'Synthetic count is 0; not verified.','citations':[]},
        ]
        report = {'reportId':'SYN-DOCX','caseId':'SYN-XREPO-001','version':1,
                  'templateId':'imo-cic','lang':'bilingual','status':'Draft',
                  'isFictionalDemo':True,'sections':[
                      {'sectionId':'analysis','titleZh':'合成分析','titleEn':'Synthetic analysis',
                       'status':'Draft','missing':True,'sentences':sentences}]}
        before = deepcopy(report)
        raw = export_report(report, format='docx', lang='bilingual', include_glossary=False)
        self.assertEqual(report, before)
        with TemporaryDirectory(prefix='mcis-synthetic-docx-') as folder:
            path = Path(folder) / 'synthetic.docx'
            path.write_bytes(raw)
            with ZipFile(path) as package:
                self.assertIsNone(package.testzip())
                body = ET.fromstring(package.read('word/document.xml'))
                self.assertIn('[Content_Types].xml', package.namelist())
                headers = [ET.fromstring(package.read(n)) for n in package.namelist()
                           if n.startswith('word/header') and n.endswith('.xml')]
                footers = [ET.fromstring(package.read(n)) for n in package.namelist()
                           if n.startswith('word/footer') and n.endswith('.xml')]
        tables = body.findall('.//' + W + 'tbl')
        self.assertEqual(len(tables), 1)
        rows = tables[0].findall(W + 'tr')
        self.assertEqual(len(rows), 3)
        self.assertEqual([text(c) for c in rows[0].findall(W+'tc')], ['中文','English'])
        for row, sentence in zip(rows[1:], sentences, strict=True):
            cells = row.findall(W+'tc')
            self.assertEqual(len(cells), 2)
            for cell, lang in zip(cells, ('Zh','En'), strict=True):
                self.assertTrue(text(cell).startswith(sentence['text'+lang]))
        pending = text(rows[1])
        self.assertIn('缺数据 / missing', pending)
        self.assertIn('需复核 / needs review', pending)
        self.assertNotIn('SYN-MISSING', text(rows[2]))
        full = text(body)
        self.assertIn('DRAFT 草稿', full)
        self.assertIn('虚构示例 / Fictional', full)
        self.assertIn('含缺数据项 / Contains missing data', full)
        self.assertNotIn('CONFIRMED 已确认', full)
        self.assertTrue(headers)
        self.assertTrue(all('DRAFT 草稿' in text(h) for h in headers))
        self.assertTrue(footers)
        self.assertTrue(all('不作责任认定' in text(f) and
                            'This report does not apportion blame or liability' in text(f) for f in footers))
        print('receipt: DOCX=1 bilingualRows=2 pendingPreserved=true zeroTextPreserved=true inputUnchanged=true temporaryRemoved=true')

if __name__ == '__main__':
    unittest.main(verbosity=2)
