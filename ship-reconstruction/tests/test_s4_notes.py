import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from s4lib.notes import parse


class Notes(unittest.TestCase):
    def test_mixed_profile_and_role(self):
        r=parse("Fr.3~Fr.9 甲板纵骨 L45x30x4")
        self.assertEqual(r["type"],"longitudinal")
        self.assertEqual(r["profiles"][0]["values"],[45,30,4])
        self.assertIsNone(r["profiles"][0]["unit"])
        self.assertEqual(r["frame_ranges"][0]["end"],9)

    def test_plate_notation(self):
        self.assertEqual(parse("连接板-5x80x90")["profiles"][0]["values"],[5,80,90])

    def test_deck_unit(self):
        self.assertEqual(parse("甲板t=7mm")["dimensions"][0]["unit"],"mm")

    def test_section_with_flange_and_unknown(self):
        for token,expected in [("T 160×7+60×8",[160,7,60,8]),("FB 65×?",[65,None])]:
            r=parse(token)
            self.assertEqual(r["profiles"][0]["values"],expected)
            self.assertEqual(r["dimensions"],[])

    def test_fraction_range_and_material(self):
        r=parse("甲板 THK 1/4 in FR -4~-2 材质 AH32")
        self.assertEqual(r["dimensions"][0]["value"],.25)
        self.assertEqual(r["dimensions"][0]["unit"],"in")
        self.assertEqual(r["frame_ranges"][0]["end"],-2)
        self.assertEqual(r["material"],"AH32")

    def test_bulkhead_plate_abbreviated_on_drawing(self):
        for text,role in [("FR 2~FR 5 纵壁板 t=4","longitudinal_bulkhead"),("横向壁板","transverse_bulkhead")]:
            self.assertEqual(parse(text)["type"],role)

    def test_each_profile_belongs_to_its_own_clause(self):
        q=parse("斜撑L65x5 连接板-6x120x140")
        self.assertEqual([v["owner_type"] for v in q["profiles"]],["brace","bracket"])
