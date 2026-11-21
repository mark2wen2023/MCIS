"""Offline actual ranking; existing jsonschema, no app imports or database."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import jsonschema

ROOT=Path(__file__).resolve().parent

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
r=load('rank');f=load('fixtures')

class Checks(unittest.TestCase):
    def test_existing_content_schema(self):
        schema=json.loads((ROOT.parents[1]/'contracts/schemas/knowledge-card.schema.json').read_text())
        for card in f.CARDS:jsonschema.Draft202012Validator(schema).validate(card['content'])

    def test_prelabelled_evaluation(self):
        original=copy.deepcopy(f.CARDS)
        result=r.rank_cases(f.QUERY,f.CARDS,reviewed_vocabulary=f.VOCABULARY)
        ids=[x['cardId'] for x in result]
        self.assertEqual(ids,[f.identity(1),f.identity(2),f.identity(9)])
        self.assertEqual(set(ids)&f.RELEVANT,{f.identity(1),f.identity(2)})
        self.assertEqual(f.RELEVANT-set(ids),{f.identity(3)})
        self.assertEqual(set(ids)-f.RELEVANT,{f.identity(9)})
        self.assertEqual(result[0]['score'],{'numerator':1,'denominator':1})
        self.assertEqual(result[1]['score'],{'numerator':2,'denominator':3})
        self.assertEqual(result[1]['sharedTags'],sorted(f.QUERY))
        self.assertEqual(f.CARDS,original)

    def test_status_kind_and_keyword_not_score(self):
        selected=[f.CARDS[i] for i in (3,4,5,6,7)]
        self.assertEqual(r.rank_cases(f.QUERY,selected,reviewed_vocabulary=f.VOCABULARY),[])
        for status in ('Rejected',None,'Unknown'):
            item=copy.deepcopy(f.CARDS[0]);item['status']=status
            self.assertEqual(r.rank_cases(f.QUERY,[item],reviewed_vocabulary=f.VOCABULARY),[])

    def test_empty_unknown(self):
        for query in ([],[''],['未知']):
            self.assertEqual(r.rank_cases(query,f.CARDS,reviewed_vocabulary=f.VOCABULARY),[])
        self.assertEqual(r.rank_cases(f.QUERY,f.CARDS,reviewed_vocabulary=[]),[])
        self.assertEqual(r.rank_cases(f.QUERY,[],reviewed_vocabulary=f.VOCABULARY),[])

    def test_ties_topfive_order_and_normalization(self):
        cards=[f.card(n,['能见度受限'],'合成') for n in range(20,27)]
        a=r.rank_cases([' 能见度受限 '],cards,reviewed_vocabulary=f.VOCABULARY)
        b=r.rank_cases(['能见度受限'],list(reversed(cards)),reviewed_vocabulary=f.VOCABULARY)
        self.assertEqual(a,b);self.assertEqual([x['cardId'] for x in a],[f.identity(n) for n in range(20,25)])
        self.assertEqual(r.tags([' Fog ','fog']),{'fog'})

    def test_ordinary_invalid_input(self):
        with self.assertRaises(ValueError):r.rank_cases(None,f.CARDS,reviewed_vocabulary=f.VOCABULARY)
        with self.assertRaises(ValueError):r.rank_cases(f.QUERY,[f.CARDS[0],f.CARDS[0]],reviewed_vocabulary=f.VOCABULARY)

if __name__=='__main__':unittest.main(verbosity=2)
