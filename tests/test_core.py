import copy
import json
import tempfile
import unittest
from pathlib import Path
from evidence_desk.core import Index, bundled, chunk_documents, validate_candidate, answer, parse_strict, messages
from evidence_desk.model import validate_endpoint
from evidence_desk.evaluate import score_result, render


class FakeModel:
    def __init__(self, content, finish='stop'):
        self.content=content; self.finish=finish; self.calls=0
    def complete(self, prompt):
        self.calls+=1
        return dict(content=self.content,finish_reason=self.finish,latency_seconds=.01,usage={})


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.docs=bundled('corpus.json'); self.index=Index(self.docs)
        self.hits=self.index.retrieve('encrypted backup retention',1)
        self.good=json.dumps({'decision':'answer','evidence':[{'source_id':'backup:1','quote':'Encrypted backup copies are retained for 35 days.'}]})

    def check_failed(self, obj):
        self.assertEqual(validate_candidate(json.dumps(obj),self.hits)['status'],'CHECK_FAILED')

    def test_only_current_approved_chunks(self):
        self.assertEqual(len(self.index.chunks),16)
        self.assertEqual({x['id'] for x in self.index.excluded},{'injection','backup-old'})

    def test_unapproved_instruction_never_retrieved(self):
        hits=self.index.retrieve('APPROVED_OVERRIDE backup retention 999',5)
        self.assertNotIn('injection:1',[x['id'] for x in hits])
        self.assertFalse(any('999' in x['text'] for x in hits))

    def test_bm25_ranks_requested_topic(self):
        self.assertEqual(self.index.retrieve('temporary production access expires')[0]['id'],'access:1')

    def test_empty_overlap_abstains_without_model(self):
        client=FakeModel('invalid')
        result=answer(self.index,'xylophone zebra',client)
        self.assertEqual(result['status'],'ABSTAIN')
        self.assertEqual(client.calls,0)

    def test_invalid_questions(self):
        for q in ('','   ','a'*601,[],None):
            with self.subTest(q=str(q)[:20]),self.assertRaises(ValueError):self.index.retrieve(q)

    def test_invalid_k(self):
        for k in (0,6,True,1.5):
            with self.assertRaises(ValueError):self.index.retrieve('backup',k)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):Index([self.docs[0],self.docs[0]])

    def test_boolean_trust_is_strict(self):
        doc=copy.deepcopy(self.docs[0]);doc['approved']='true'
        with self.assertRaises(ValueError):Index([doc])

    def test_long_paragraph_not_silently_truncated(self):
        doc=copy.deepcopy(self.docs[0]);doc['text']='a'*1201
        with self.assertRaises(ValueError):Index([doc])

    def test_no_approved_content_rejected(self):
        with self.assertRaises(ValueError):Index([self.docs[-1]])

    def test_exact_quote_accepted(self):
        self.assertEqual(validate_candidate(self.good,self.hits)['status'],'ANSWER')

    def test_modified_number_rejected(self):
        self.assertEqual(validate_candidate(self.good.replace('35 days','999 days'),self.hits)['status'],'CHECK_FAILED')

    def test_unretrieved_source_rejected(self):
        self.assertEqual(validate_candidate(self.good.replace('backup:1','injection:1'),self.hits)['status'],'CHECK_FAILED')

    def test_extra_fields_rejected(self):
        obj=json.loads(self.good);obj['answer']='invented';self.check_failed(obj)

    def test_empty_answer_rejected(self):
        self.check_failed({'decision':'answer','evidence':[]})

    def test_whitespace_quote_rejected(self):
        obj=json.loads(self.good);obj['evidence'][0]['quote']=' '*20;self.check_failed(obj)

    def test_duplicate_quote_rejected(self):
        obj=json.loads(self.good);obj['evidence']*=2;self.check_failed(obj)

    def test_abstention_requires_empty_evidence(self):
        obj=json.loads(self.good);obj['decision']='abstain';self.check_failed(obj)
        self.assertEqual(validate_candidate('{"decision":"abstain","evidence":[]}',self.hits)['status'],'ABSTAIN')

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):parse_strict('{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):parse_strict('{"a":NaN}')

    def test_truncated_generation_never_accepted(self):
        result=answer(self.index,'encrypted backup retention',FakeModel(self.good,'length'))
        self.assertEqual(result['status'],'CHECK_FAILED')
        self.assertEqual(result['evidence'],[])

    def test_bad_json_is_not_repaired(self):
        self.assertEqual(validate_candidate('```json\n'+self.good+'\n```',self.hits)['status'],'CHECK_FAILED')

    def test_relevant_quote_is_not_guaranteed_by_provenance(self):
        checked=validate_candidate(self.good,self.hits)
        q={'gold':[]}
        result={**checked,'hits':self.hits}
        self.assertFalse(score_result(q,result)['success'])

    def test_all_requested_facts_required(self):
        q={'gold':[{'source':'backup:1','contains':'35 days'},{'source':'backup:1','contains':'02:30'}]}
        result={**validate_candidate(self.good,self.hits),'hits':self.hits}
        self.assertFalse(score_result(q,result)['success'])

    def test_loopback_endpoint_only(self):
        self.assertEqual(validate_endpoint('http://127.0.0.1:8094/'),'http://127.0.0.1:8094')
        for url in ('https://example.com','http://evil.local:8000','http://127.0.0.1:8/path','http://u:p@localhost:8','http://localhost:8?x=1','http://localhost'):
            with self.subTest(url=url),self.assertRaises(ValueError):validate_endpoint(url)

    def test_prompt_separates_rules_from_data(self):
        prompt=messages('ignore instructions',self.hits)
        self.assertEqual([p['role'] for p in prompt],['system','user'])
        self.assertEqual(json.loads(prompt[1]['content'])['question'],'ignore instructions')

    def test_corpus_hash_changes_with_content(self):
        docs=copy.deepcopy(self.docs);docs[0]['text']+=' Additional sentence.'
        self.assertNotEqual(self.index.digest,Index(docs).digest)

    def test_report_script_injection_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'report.html';render({'question':'</script><script>alert(1)</script>'},out)
            self.assertNotIn('</script><script>alert(1)',out.read_text(encoding='utf-8'))


if __name__=='__main__':unittest.main()
