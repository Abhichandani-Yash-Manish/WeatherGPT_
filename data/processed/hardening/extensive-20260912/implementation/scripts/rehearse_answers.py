"""Complete question-to-answer replay using hash-verified stored provider responses."""
import argparse
import json
import sys
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rehearse_ingestion import rehearse
from weathergpt_data.answers import AnswerService
from weathergpt_data.geography import Geography
from weathergpt_data.ingestion import IngestionDB
from weathergpt_data.transport import parsed


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    ingestion=rehearse(output/'ingestion')
    now=datetime(2026,9,11,20,tzinfo=timezone.utc)
    geo=ROOT/'data/processed/geography/source-inventory-20260912-v1/geography.sqlite'
    g=Geography(geo,readonly=True)
    try:
        candidates=g.resolve('Ahmedabad',namespace='S24',kind='place')['candidates']
        if len(candidates)!=1:raise ValueError('Replay needs the frozen, unique S24 Ahmedabad place candidate')
        entity=candidates[0]['entity_id']
    finally:g.close()
    service=AnswerService(output/'ingestion/ingestion.sqlite',output/'ingestion/raw',geo,clock=lambda:now)
    question='How much rain is forecast for Ahmedabad today from 09:30 to 12:30?'
    examples={
        'ambiguous_location':service.answer(question),
        'ahmedabad_rain':service.answer(question,entity_id=entity),
        'ahmedabad_weather':service.answer(question.replace('How much rain is forecast','What is the weather forecast'),entity_id=entity),
        'half_hour_boundary':service.answer(question.replace('09:30','09:00').replace('12:30','12:00'),entity_id=entity),
        'vadodara_source_candidates':service.answer(question.replace('Ahmedabad','Vadodara')),
        'unknown_location':service.answer(question.replace('Ahmedabad','Unlisted test locality')),
        'official_warning_gate':service.answer('Is there an official warning for Ahmedabad?'),
        'crop_advice_gate':service.answer('What is the current advisory for my crop?'),
        'aviation_gate':service.answer('Is my flight safe?'),
        'marine_gate':service.answer('Is it safe for fishing?'),
    }
    expected={'ambiguous_location':'needs_selection','ahmedabad_rain':'prototype_answer','ahmedabad_weather':'prototype_answer',
              'half_hour_boundary':'partial','vadodara_source_candidates':'needs_selection','unknown_location':'unavailable','official_warning_gate':'unavailable',
              'crop_advice_gate':'unavailable','aviation_gate':'unavailable','marine_gate':'unavailable'}
    for name,status in expected.items():
        if examples[name]['status']!=status:raise ValueError((name,examples[name]))
    source=ROOT/'data/processed/foundation/20260911T194849Z/forecast-ahmedabad.json'
    original=json.loads(source.read_text())
    raw=json.loads((ROOT/'data/runtime'/original['provenance']['blob']).read_bytes())
    answer=examples['ahmedabad_rain'];start=parsed(answer['request']['start_utc']).timestamp();end=parsed(answer['request']['end_utc']).timestamp()
    independently_summed=sum((Decimal(str(v)) for t,v in zip(raw['hourly']['time'],raw['hourly']['precipitation']) if start<t<=end),Decimal(0))
    if Decimal(answer['values'][0]['value_decimal'])!=independently_summed:raise ValueError('Answer differs from independent raw-response sum')
    # The same serving code works for every saved land sample without city-specific branches.
    db=IngestionDB(output/'ingestion/ingestion.sqlite',clock=lambda:now,readonly=True)
    try:
        before=db.status()
        for i,row in enumerate(db.db.execute('SELECT result FROM versions')):
            value=json.loads(row[0])
            if value['source_id']!='S21':continue
            example=service.answer(question.replace('Ahmedabad','selected point'),coordinates=value['coverage']['requested_point'])
            if example['status']!='prototype_answer':raise ValueError(example)
            examples['national_land_sample_'+str(i)]=example
        if db.status()!=before:raise ValueError('Answer serving mutated the ingestion database')
    finally:db.close()
    for result in examples.values():
        result['evidence_mode']='historical_saved_response_replay'
        result['answer']='Historical replay, not current weather. '+result['answer']
    report={'mode':'historical_saved_response_replay','replay_clock_utc':now.isoformat(),
            'scope':'Actual saved source values replayed through ingestion and answering; retrieval timestamps in replay are simulated.',
            'original_ahmedabad_provenance':original['provenance'],'real_provider_calls':0,
            'ingestion_jobs':ingestion['jobs'],'published_scalar_records':ingestion['measurements']['published_scalar_records'],
            'normal_backup_restore':ingestion['backup_restore'],'independent_raw_rain_sum_mm':str(independently_summed),
            'answer_count':len(examples),'statuses':{k:v['status'] for k,v in examples.items()},'operational_ready':False}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'answers.json').write_text(json.dumps(examples,indent=2,ensure_ascii=False)+'\n')
    (output/'example-answer.md').write_text('# First grounded forecast answer\n\n'+examples['ahmedabad_rain']['answer']+
        '\n\n**Question:** '+question+'\n\nThe city point was selected after the initial response exposed the city/district ambiguity. '
        'The rainfall total also matches an independent sum of the original response values.\n\n'
        '**Half-hour boundary case:** '+examples['half_hour_boundary']['answer']+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    print(json.dumps(run(parser.parse_args().output),indent=2))
