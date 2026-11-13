import unittest
from panel import Panel, ROLES
class Tests(unittest.TestCase):
    def setUp(self): self.p = Panel({'reportVersion':1,'sources':['A','B']})
    def test_snapshot_copy(self):
        packet=self.p.packet('vessel');packet['snapshot']['sources'].append('X')
        self.assertNotIn('X',self.p.packet('vessel')['snapshot']['sources'])
    def test_unknown_role(self):
        with self.assertRaises(ValueError):self.p.packet('judge')
    def test_no_unread_citation(self):
        with self.assertRaises(ValueError):self.p.review('vessel','x',['A'])
    def test_read_then_review(self):
        self.p.record_read('vessel','A');self.p.review('vessel','x',['A'])
        self.assertEqual('independent',self.p.phase)
    def test_blind_packet(self):
        self.p.review('vessel','peer view',[])
        self.assertNotIn('reviews',self.p.packet('navigation'))
    def test_no_early_challenge(self):
        with self.assertRaises(ValueError):self.p.challenge('vessel','navigation','x',[])
    def test_all_four_required(self):
        for r in ROLES:self.p.review(r,'may be unknown',[])
        self.assertEqual('cross_examination',self.p.phase)
        self.p.challenge('vessel','navigation','why?',[])
        self.assertEqual(1,len(self.p.turns))
    def test_duplicate_review_rejected(self):
        self.p.review('vessel','x',[])
        with self.assertRaises(ValueError):self.p.review('vessel','y',[])
    def test_cancel_prevents_new_turn(self):
        self.p.cancel()
        with self.assertRaises(ValueError):self.p.review('vessel','x',[])
    def test_unknown_source(self):
        with self.assertRaises(ValueError):self.p.record_read('vessel','X')
    def test_first_pass_has_no_peer_context_at_each_step(self):
        for role in sorted(ROLES):
            packet = self.p.packet(role)
            self.assertEqual('independent', packet['phase'])
            self.assertNotIn('reviews', packet)
            self.assertNotIn('turns', packet)
            self.p.review(role, role+' initial review', [])
    def test_cross_context_contains_all_first_reviews(self):
        for role in ROLES:self.p.review(role,role+' initial review',[])
        packet = self.p.packet('vessel')
        self.assertEqual(ROLES,set(packet['reviews']))
        self.assertEqual('navigation initial review',packet['reviews']['navigation']['text'])
        self.assertEqual([],packet['turns'])
    def test_later_turn_sees_prior_turns_in_order(self):
        for role in ROLES:self.p.review(role,'initial',[])
        self.p.challenge('vessel','navigation','question one',[])
        first_packet=self.p.packet('navigation')
        self.assertEqual('question one',first_packet['turns'][0]['text'])
        self.p.challenge('navigation','vessel','response two',[])
        later_packet=self.p.packet('investigation')
        self.assertEqual(['question one','response two'],[t['text'] for t in later_packet['turns']])
        self.assertEqual(1,len(first_packet['turns']))
    def test_cross_packet_is_deep_copy_of_reviews_and_turns(self):
        for role in ROLES:
            self.p.record_read(role,'A');self.p.review(role,'original',['A'])
        self.p.challenge('vessel','navigation','original challenge',['A'])
        packet=self.p.packet('navigation')
        packet['reviews']['vessel']['text']='tampered'
        packet['reviews']['vessel']['refs'].append('X')
        packet['turns'][0]['refs'].clear()
        packet['turns'].append({'text':'fake'})
        fresh=self.p.packet('regulation')
        self.assertEqual('original',fresh['reviews']['vessel']['text'])
        self.assertEqual(['A'],fresh['reviews']['vessel']['refs'])
        self.assertEqual(['A'],fresh['turns'][0]['refs'])
        self.assertEqual(1,len(fresh['turns']))
if __name__ == '__main__':unittest.main()
