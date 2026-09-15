"""Functional HTTP journeys and refresh boundaries for the local workspace."""
import json
import re
import threading
import unittest
import urllib.error
import urllib.request
from datetime import timedelta
from unittest.mock import patch
import test_answers as fixture
from test_ingestion import Response,payload
from weathergpt_data.workspace import Workspace,make_server

class WorkspaceTests(unittest.TestCase):
    publish=fixture.AnswerTests.publish
    add_place=fixture.AnswerTests.add_place
    ask=fixture.AnswerTests.ask

    def setUp(self):
        fixture.AnswerTests.setUp(self)
        self.calls=0
        def opener(*args,**kwargs):
            self.calls+=1
            return Response(json.dumps(payload()).encode())
        self.app=Workspace(self.root/'jobs.sqlite',self.root/'raw',self.root/'geography.sqlite',clock=lambda:self.now,opener=opener)
        self.body={'question':fixture.QUESTION}

    def test_answer_then_fresh_refresh_make_no_provider_call(self):
        packet=self.app.answer(self.body)
        self.assertEqual(packet['answer']['status'],'prototype_answer')
        self.assertEqual(packet['context']['status'],'eligible_prototype')
        packet=self.app.refresh(self.body)
        self.assertEqual(packet['refresh']['state'],'already_fresh');self.assertEqual(self.calls,0)

    def test_stale_to_refreshed_and_repeated_click_is_noop(self):
        self.now+=timedelta(minutes=61)
        self.assertEqual(self.app.answer(self.body)['answer']['status'],'stale')
        packet=self.app.refresh(self.body)
        self.assertEqual(packet['refresh']['state'],'succeeded');self.assertEqual(self.calls,1)
        self.assertEqual(packet['refresh']['job_provider_attempts'],1)
        self.assertEqual(packet['answer']['status'],'prototype_answer')
        self.assertEqual(self.app.refresh(self.body)['refresh']['state'],'already_fresh');self.assertEqual(self.calls,1)

    def test_bad_refresh_retains_previous_evidence_and_does_not_retry_terminal_job(self):
        self.now+=timedelta(minutes=1)
        # Trigger a fresh collection at a different point with no prior snapshot.
        body={'question':fixture.QUESTION.replace('Ahmedabad','selected point'),'coordinates':{'latitude':24.,'longitude':72.5}}
        self.app.opener=lambda *a,**k:Response(b'{}')
        packet=self.app.refresh(body);self.assertEqual(packet['refresh']['state'],'failed')
        self.assertEqual(packet['answer']['status'],'unavailable');self.assertFalse(packet['context']['evidence'])
        packet=self.app.refresh(body);self.assertEqual(packet['refresh']['claims_this_action'],0)
        self.assertEqual(self.ask()['status'],'prototype_answer')

    def test_policy_hold_prevents_collection(self):
        policy=self.root/'held.json';policy.write_text('{"schema_version":"answer-policy-v1","sources":{"S21":{"enabled":false}}}')
        self.app.service.policy_path=policy
        with self.assertRaises(ValueError):self.app.refresh(self.body)
        self.assertEqual(self.calls,0)

    def test_refresh_requires_spatial_temporal_and_supported_contract(self):
        district=self.add_place(kind='district',code='district')
        for body in [self.body,{**self.body,'entity_id':district},{'question':'Are there official warnings?'},
                     {'question':fixture.QUESTION.replace('tomorrow','today'),'entity_id':self.entity},
                     {'question':fixture.QUESTION.replace('tomorrow','on 2026-09-25'),'entity_id':self.entity}]:
            with self.subTest(body=body),self.assertRaises(ValueError):self.app.refresh(body)
        self.assertEqual(self.calls,0)

    def test_http_clarification_selection_and_refresh_round_trip(self):
        self.add_place(kind='district',code='district');self.now+=timedelta(minutes=61)
        server=make_server(self.app,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join()))
        base='http://127.0.0.1:'+str(server.server_port)
        html=urllib.request.urlopen(base).read().decode()
        token=re.search(r'name="workspace-token" content="([^"]+)"',html)[1]
        def post(path,body,extra=None):
            headers={'Content-Type':'application/json','X-WeatherGPT-Token':token}
            headers.update(extra or {})
            with urllib.request.urlopen(urllib.request.Request(base+path,json.dumps(body).encode(),headers)) as response:
                self.assertEqual(response.headers['Cache-Control'],'no-store')
                return json.load(response)
        packet=post('/api/answer',self.body)
        choices=packet['context']['clarification']['candidates']
        city=next(c for c in choices if c['kind']=='place')
        selected={**self.body,'entity_id':city['entity_id']}
        self.assertEqual(post('/api/answer',selected)['answer']['status'],'stale')
        self.assertEqual(post('/api/refresh',selected)['answer']['status'],'prototype_answer')
        self.assertEqual(self.calls,1)
        for headers in [{'X-WeatherGPT-Token':''},{'Origin':'https://unrelated.example'},{'Host':'unrelated.example'}]:
            with self.subTest(headers=headers),self.assertRaises(urllib.error.HTTPError) as error:post('/api/refresh',selected,headers)
            self.assertEqual(error.exception.code,403)
        self.assertEqual(self.calls,1)
        with self.assertRaises(urllib.error.HTTPError) as error:post('/api/answer',{'question':fixture.QUESTION,'url':'https://example.com'})
        self.assertEqual(error.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(base+'/api/refresh')
        self.assertEqual(error.exception.code,404)

    def test_http_progress_route_is_token_gated_and_reports_facts(self):
        server=make_server(self.app,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join()))
        base='http://127.0.0.1:'+str(server.server_port)
        html=urllib.request.urlopen(base).read().decode()
        token=re.search(r'name="workspace-token" content="([^"]+)"',html)[1]
        with urllib.request.urlopen(urllib.request.Request(base+'/api/chat/progress',
                headers={'X-WeatherGPT-Token':token})) as response:
            self.assertEqual(response.headers['Cache-Control'],'no-store')
            packet=json.load(response)
        self.assertEqual(packet['state'],'idle')
        self.assertTrue(packet['stages_are_facts_not_progress'])
        self.assertNotIn('%',json.dumps(packet))
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(base+'/api/chat/progress')
        self.assertEqual(error.exception.code,403)

if __name__=='__main__':unittest.main()
