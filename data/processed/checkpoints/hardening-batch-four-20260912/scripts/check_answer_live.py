"""Explicit single-job live check using the shared default ingestion database/budget."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from weathergpt_data.answers import AnswerService
from weathergpt_data.geography import Geography
from weathergpt_data.ingestion import IngestionDB,run_batch
from weathergpt_data.transport import utcnow


def check(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    geo_path=ROOT/'data/processed/geography/source-inventory-20260912-v1/geography.sqlite'
    geo=Geography(geo_path,readonly=True)
    try:
        matches=geo.resolve('Ahmedabad',namespace='S24',kind='place')['candidates']
        if len(matches)!=1:raise ValueError('Select a unique source place before collecting')
        entity=geo.get(matches[0]['entity_id']);lon,lat=entity['geometry']['coordinates']
    finally:geo.close()
    database=ROOT/'data/runtime/ingestion/ingestion.sqlite';raw=ROOT/'data/runtime/ingestion/raw'
    db=IngestionDB(database)
    try:
        before=db.status()['network_attempts_reserved']
        # Repeated checks within an hour share one explicitly planned collection identity.
        cycle=utcnow().replace(minute=0,second=0,microsecond=0).isoformat()
        jid=db.enqueue('forecast',lat,lon,3,cycle)
        worker=run_batch(db,raw,max_jobs=1)
        attempts=db.status()['network_attempts_reserved']-before
    finally:db.close()
    question='How much rain is forecast for Ahmedabad tomorrow from 09:30 to 12:30?'
    result=AnswerService(database,raw,geo_path).answer(question,entity_id=entity['entity_id'])
    report={'mode':'live_single_bounded_check','checked_at_utc':utcnow().isoformat(),'target_job_id':jid,
            'worker':worker,'governed_attempts_reserved':attempts,'answer_status':result['status'],
            'answer_provider_calls':result['provider_calls'],'operational_ready':False}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'answer.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    (output/'answer.md').write_text('# Ahmedabad forecast workflow check\n\n**Question:** '+question+'\n\n'+result['answer']+
                                  '\n\nThis is one access and answer-contract check. It does not establish sustained reliability or forecast skill.\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    print(json.dumps(check(parser.parse_args().output),indent=2))
