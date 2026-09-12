"""Offline review probes; uses temporary fixtures and never fetches weather or changes production data."""
import json
import sys
from datetime import timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import test_answers as fixture
from test_ingestion import Response
from weathergpt_data.ingestion import run_one
from weathergpt_data.rag import context


def run():
    findings=[]
    f=fixture.AnswerTests();f.setUp()
    try:
        f.now+=timedelta(minutes=1)
        failed=f.db.enqueue('forecast',23.,72.5,7,f.now.isoformat())
        worker=run_one(f.db,f.root/'raw',lambda *a,**k:Response(b'{}'))
        answer=f.ask();packet=context(f.service,fixture.QUESTION)
        findings.append({'id':'WC01','worker_state':worker['state'],'newer_failed_job':failed,
                         'answer_status':answer['status'],'rag_status':packet['status'],
                         'reported_refresh_health':answer['freshness']['refresh_health'],
                         'gap_reproduced':worker['state']=='failed' and packet['status']=='eligible_prototype',
                         'expected':'A newer failed due collection for this point must be disclosed; ordinary RAG evidence must abstain.'})
    finally:f.doCleanups()
    f=fixture.AnswerTests();f.setUp()
    try:
        f.add_place(kind='district',code='district')
        answer=f.ask();packet=context(f.service,fixture.QUESTION)
        candidates=answer['location']['candidates']
        present=all(c['entity_id'] in json.dumps(packet) for c in candidates)
        findings.append({'id':'WC02','answer_candidate_count':len(candidates),'rag_status':packet['status'],
                         'candidate_ids_present_in_packet':present,'gap_reproduced':len(candidates)>1 and not present,
                         'expected':'Keep numeric abstention, but return structured candidate choices or an explicit resolver action.'})
    finally:f.doCleanups()
    return {'mode':'synthetic_offline_review','provider_calls':0,'llm_calls':0,'findings':findings}


if __name__=='__main__':print(json.dumps(run(),indent=2))
