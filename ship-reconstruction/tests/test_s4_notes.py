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
