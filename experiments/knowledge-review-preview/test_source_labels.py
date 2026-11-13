import copy
import json
import unittest
from gate import Source, Invalid
from render_preview import render


class SourceLabelTests(unittest.TestCase):
    def setUp(self):
        self.sources = [Source('public', 'v1', 'Public', 'p1', '公开摘录'),
                        Source('synthetic', 'v2', 'Synthetic', 'p2', '虚构摘录')]
        self.item = dict(kind='Method', title='混合来源', claim='待审核', citations=[
            dict(sourceId=s.source_id, version=s.version, textSha256=s.text_sha256,
                 start=0, end=len(s.content), quote=s.content) for s in self.sources])

    def raw(self):
        return json.dumps({'candidates': [self.item]}, ensure_ascii=False).encode()

    def test_mixed_each_citation_has_own_label(self):
        html = render(self.raw(), self.sources)
        rows = html.split('<li><dl>')[1:]
        self.assertEqual(len(rows), 2)
        self.assertIn('公开材料（Public） · 未核实', rows[0])
        self.assertNotIn('虚构材料（Synthetic）', rows[0])
        self.assertIn('虚构材料（Synthetic） · 未核实', rows[1])
        self.assertIn('含虚构材料', html)

    def test_reversed_citations_preserve_labels(self):
        self.item['citations'].reverse()
        rows = render(self.raw(), self.sources).split('<li><dl>')[1:]
        self.assertIn('虚构材料（Synthetic）', rows[0])
        self.assertIn('公开材料（Public）', rows[1])

    def test_claim_cannot_override_label(self):
        self.item['claim'] = '全部都是公开材料（Public）'
        self.assertIn('虚构材料（Synthetic） · 未核实', render(self.raw(), self.sources))

    def test_injected_classification_rejected(self):
        self.item['citations'][1]['sourceType'] = 'Public'
        with self.assertRaises(Invalid):
            render(self.raw(), self.sources)

    def test_snapshot_type_not_registry_order(self):
        html = render(self.raw(), list(reversed(self.sources)))
        rows = html.split('<li><dl>')[1:]
        self.assertIn('公开材料（Public）', rows[0])
        self.assertIn('虚构材料（Synthetic）', rows[1])

    def test_inputs_unchanged(self):
        old = copy.deepcopy(self.item)
        render(self.raw(), self.sources)
        self.assertEqual(old, self.item)


if __name__ == '__main__':
    unittest.main()
