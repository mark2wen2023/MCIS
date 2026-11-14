"""Independent blind projection/content audit. No network or real credentials."""
import copy,json,unittest
from pathlib import Path
import blind_host as h

class BlindInputAudit(unittest.TestCase):
    def setUp(self):
        self.corpus=json.loads(Path(h.__file__).with_name('yangze22-provisional.json').read_text())
        self.cases,self.mapping=h.project()
    def test_projection_preserves_all_source_claim_fields(self):
        self.assertEqual(len(self.cases),11)
        for n,(case,original) in enumerate(zip(self.cases,self.corpus['items']),1):
            self.assertEqual(set(case),{'id','sourceText','sourceSha256','sourceLocator','claim','citation'})
            self.assertEqual(case['id'],f'case_{n:03d}')
            self.assertEqual(self.mapping[case['id']],original['id'])
            for k in set(case)-{'id'}:self.assertEqual(case[k],original[k])
        self.assertEqual(sum(x['suggestedLabel'] is None for x in self.corpus['items']),2)
    def test_every_provider_message_and_tool_result_is_blind(self):
        # All three uniform-label submissions pass the same schema-only validator:
        # it neither consults suggested labels nor exposes their agreement count.
        for chosen in ['supported','conflicted','insufficient']:
            captured=[];results=[];rounds=iter([1,2,3])
            def transport(_key,messages,_deadline):
                captured.append(copy.deepcopy(messages));r=next(rounds)
                if r==3:return {'message':{'role':'assistant','content':h.MARKER},'finish_reason':'stop'}
                name='read_blind_cases' if r==1 else 'validate_predictions'
                args={} if r==1 else {'content':json.dumps({'predictions':[{'itemId':x['id'],'label':chosen,'rationale':'independent transport stub'} for x in self.cases]})}
                return {'message':{'role':'assistant','content':None,'tool_calls':[{'id':f'call{r}','type':'function','function':{'name':name,'arguments':json.dumps(args)}}]},'finish_reason':'tool_calls'}
            host=h.Host(self.cases,self.mapping,fixture=False,key='sk-offline-test-only',transport=transport)
            for round in range(1,4):
                host.dispatch({'op':'model_start'});host.dispatch({'op':'model_request'})
                msg=host.dispatch({'op':'request_attempt_ack','attempt':round})['message']
                host.dispatch({'op':'model_end'})
                for tc in msg.get('tool_calls',[]):
                    results.append(host.dispatch({'op':'tool','name':tc['function']['name'],'args':json.loads(tc['function']['arguments']),'callId':tc['id']}))
            self.assertEqual(len(captured),3)
            self.assertEqual(results[0],{'cases':self.cases,'coordinates':'unicode_code_points'})
            self.assertEqual(results[1],{'status':'validated','schemaOnly':True,'semanticSupportVerified':False})
            serial=json.dumps(captured,ensure_ascii=False)
            for original in self.corpus['items']:
                self.assertNotIn(original['id'],serial)
                self.assertNotIn(original['rationale'],serial)
            for forbidden in ['suggestedLabel','fixture-predictions','reviewers','opinions','scripted_fixture']:
                self.assertNotIn(forbidden,serial)
            # Remapping happens only in terminal host output, not a provider turn.
            final=host.dispatch({'op':'final','payload':h.MARKER})
            self.assertEqual([p['itemId'] for p in final['predictions']['predictions']],[x['id'] for x in self.corpus['items']])
            self.assertFalse(final['factActivated'])
            self.assertEqual(len(captured),3)

if __name__=='__main__':unittest.main()
