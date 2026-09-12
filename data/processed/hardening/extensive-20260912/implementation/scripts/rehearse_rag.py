"""Demonstrate gated RAG context using a previously completed ingestion replay."""
import argparse,json,sys
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from weathergpt_data.answers import AnswerService
from weathergpt_data.rag import context
from weathergpt_data.geography import Geography


def run(replay,output):
    replay=Path(replay);output=Path(output);output.mkdir(parents=True,exist_ok=False)
    geo=ROOT/'data/processed/geography/source-inventory-20260912-v1/geography.sqlite'
    g=Geography(geo,readonly=True)
    try:entity=g.resolve('Ahmedabad',namespace='S24',kind='place')['candidates'][0]['entity_id']
    finally:g.close()
    service=AnswerService(replay/'ingestion/ingestion.sqlite',replay/'ingestion/raw',geo,clock=lambda:datetime(2026,9,11,20,tzinfo=timezone.utc))
    question='How much rain is forecast for Ahmedabad today from 09:30 to 12:30?'
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline rehearsal cannot fetch')):
        packets={'selected_ahmedabad':context(service,question,entity_id=entity),
                 'ambiguous_ahmedabad':context(service,question),
                 'split_rain_interval':context(service,question.replace('09:30','09:00'),entity_id=entity),
                 'crop_advice':context(service,'What is the current advisory for my crop?'),
                 'official_warning':context(service,'Is there an official warning for Ahmedabad?')}
        for name,packet in packets.items():
            expected='eligible_prototype' if name=='selected_ahmedabad' else 'abstain'
            if packet['status']!=expected:raise ValueError((name,packet))
            packet['evidence_mode']='historical_saved_response_replay'
            packet['deterministic_answer']='Historical replay; not current weather. '+packet['deterministic_answer']
        current=AnswerService(ROOT/'data/runtime/ingestion/ingestion.sqlite',ROOT/'data/runtime/ingestion/raw',geo)
        current_packet=context(current,question.replace('today','tomorrow'),entity_id=entity)
    (output/'contexts.json').write_text(json.dumps(packets,indent=2,ensure_ascii=False)+'\n')
    (output/'current-store-status.json').write_text(json.dumps(current_packet,indent=2,ensure_ascii=False)+'\n')
    summary={'historical_replay_statuses':{k:v['status'] for k,v in packets.items()},'current_store_status':current_packet['status'],'current_answer_status':current_packet['answer_status'],'real_provider_calls':0,'llm_calls':0,'scope':'Evidence gate only. No language-model generation or unrestricted document retrieval has been evaluated.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--replay',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(run(a.replay,a.output),indent=2))
