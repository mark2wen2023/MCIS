import unittest
from workflow import Workflow, Conflict

class Tests(unittest.TestCase):
    def setUp(self): self.w=Workflow('case1'); self.n=0
    def put(self, kind, payload, cap):
        self.n+=1
        return self.w.append('investigator',cap,str(self.n),self.w.revision,kind,payload)
    def assess(self):
        p=dict(text='preliminary',sources=self.w.sources)
        if self.w.latest_assessment: p.update(changeReason='new evidence',supersedes=self.w.latest_assessment)
        return self.put('Assessment',p,'assess')
    def verify(self):
        self.put('BeginVerification',dict(question='time?',method='compare'),'verify')
        self.put('Verification',dict(activity='reviewed',result='uncertain',outcome='Inconclusive'),'verify')
    def ready(self):
        self.assess();self.verify();self.put('SubmitDiscussion',dict(agenda='resolve times'),'verify')
    def discuss(self): return self.put('Discussion',dict(packetRevision=self.w.packet['revision'],summary='not established',dissent=['unresolved'],participantsRecorded=['A'],outcome='Undetermined'),'discuss')
    def test_full_flow_preserves_uncertainty(self):
        self.ready(); self.discuss(); self.assertEqual(self.w.stage,'DiscussionRecorded');self.assertEqual(self.w.events[-1]['payload']['outcome'],'Undetermined')
    def test_ai_cannot_write(self):
        with self.assertRaises(PermissionError): self.w.append('AgentService','assess','1',1,'Assessment',{})
    def test_revision_conflict(self):
        self.assess()
        with self.assertRaises(Conflict): self.w.append('investigator','assess','other',1,'Assessment',{})
    def test_boolean_revision(self):
        with self.assertRaises(Conflict): self.w.append('investigator','assess','1',True,'Assessment',{})
    def test_idempotency(self):
        p=dict(text='a',sources={}); a=self.w.append('investigator','assess','id',1,'Assessment',p)
        b=self.w.append('investigator','assess','id',1,'Assessment',p);self.assertEqual(a,b);self.assertEqual(len(self.w.events),1)
    def test_request_reuse(self):
        self.w.append('investigator','assess','id',1,'Assessment',dict(text='a',sources={}))
        with self.assertRaises(Conflict): self.w.append('investigator','assess','id',1,'Assessment',dict(text='b',sources={}))
    def test_no_verification_skip(self):
        self.assess()
        with self.assertRaises(Conflict): self.put('SubmitDiscussion',dict(agenda='skip'),'verify')
    def test_failed_write_no_mutation(self):
        old=self.w.snapshot()
        with self.assertRaises(ValueError): self.put('NewEvidence',dict(sourceId='s',version='1',digest='x',caseId='other'),'record')
        self.assertEqual(old,self.w.snapshot())
    def test_new_evidence_retains_history(self):
        self.ready();self.discuss();old=self.w.snapshot()
        self.put('NewEvidence',dict(sourceId='s',version='1',digest='x',caseId='case1'),'record')
        self.assertEqual(self.w.stage,'DiscussionRecorded');self.assertTrue(self.w.pending);self.assertEqual(old['events'],self.w.events[:-1])
    def test_new_evidence_invalidates_discussion_packet(self):
        self.ready();self.put('NewEvidence',dict(sourceId='s',version='1',digest='x',caseId='case1'),'record')
        with self.assertRaises(Conflict): self.discuss()
    def test_revised_assessment_keeps_prior(self):
        self.assess();self.assess();self.assertEqual(len(self.w.events),2);self.assertEqual(self.w.events[-1]['payload']['supersedes'],1)
    def test_source_version_immutable(self):
        p=dict(sourceId='s',version='1',digest='x',caseId='case1');self.put('NewEvidence',p,'record');p['digest']='y'
        with self.assertRaises(Conflict): self.put('NewEvidence',p,'record')
    def test_snapshot_is_not_mutable_reference(self):
        self.assess();s=self.w.snapshot();s['events'].clear();self.assertEqual(len(self.w.events),1)
    def test_reopen_retains_discussion(self):
        self.ready();self.discuss();self.put('Reopen',dict(reason='new material'),'assess');self.assertEqual(self.w.stage,'AssessmentRecorded');self.assertTrue(any(x['kind']=='Discussion' for x in self.w.events))
    def test_more_verification_requires_new_round_evidence(self):
        self.ready(); old_packet = self.w.packet.copy()
        self.put('Discussion',dict(packetRevision=self.w.packet['revision'],summary='check again',dissent=[],participantsRecorded=['A'],outcome='MoreVerification'),'discuss')
        before = self.w.snapshot()
        with self.assertRaises(Conflict): self.put('SubmitDiscussion',dict(agenda='skip round'),'verify')
        self.assertEqual(before,self.w.snapshot())
        self.assertEqual(self.w.verification_round,old_packet['verificationRound']+1)
        self.put('Verification',dict(activity='new check',result='still uncertain',outcome='Inconclusive'),'verify')
        self.put('SubmitDiscussion',dict(agenda='new round'),'verify')
        self.assertFalse(set(old_packet['verificationIds']) & set(self.w.packet['verificationIds']))
        self.assertEqual(self.w.events[3]['payload']['packet'],old_packet)
    def test_reopen_begin_requires_fresh_verification(self):
        self.ready(); self.discuss(); old=self.w.snapshot()['events']
        self.put('Reopen',dict(reason='recheck'),'assess')
        self.put('BeginVerification',dict(question='again?',method='new review'),'verify')
        with self.assertRaises(Conflict): self.put('SubmitDiscussion',dict(agenda='skip'),'verify')
        self.assertEqual(old,self.w.events[:len(old)])
        self.assertEqual(self.w.verifications,[])
    def test_more_verification_repeat_does_not_reset_new_evidence(self):
        self.ready()
        payload=dict(packetRevision=self.w.packet['revision'],summary='check',dissent=[],participantsRecorded=[],outcome='MoreVerification')
        rev=self.w.revision
        self.w.append('investigator','discuss','repeat',rev,'Discussion',payload)
        self.put('Verification',dict(activity='new',result='none',outcome='Inconclusive'),'verify')
        before=self.w.snapshot()
        self.w.append('investigator','discuss','repeat',rev,'Discussion',payload)
        self.assertEqual(before,self.w.snapshot())
if __name__=='__main__': unittest.main()
