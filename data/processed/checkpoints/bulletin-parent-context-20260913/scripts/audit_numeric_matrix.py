"""Independent source-value oracles across every stored forecast interval and national cell."""
import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from weathergpt_data.answers import calculate
from weathergpt_data.adapters import hourly,FORECAST
from weathergpt_data.transport import parsed


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    counts=Counter();per_source={};assets=json.loads((ROOT/'data/registry/assets.json').read_text())['files']
    for item in assets:
        if hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Registered evidence changed: '+item['path'])
        counts['registered_assets_hash_verified']+=1
    db=ROOT/'data/processed/climate/national-climate-v1-a203fc0eb4a31c58/climate.sqlite'
    tables={}
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('National database integrity')
        for r in con.execute('SELECT * FROM climate_records'):
            source=r['raw_asset_path']
            if source not in tables:
                with (ROOT/source).open(encoding='utf-8-sig',newline='') as stream:tables[source]=list(csv.DictReader(stream))
            native=tables[source][r['source_row']-2]
            if native['Year']!=str(r['year']) or native[r['source_column']]!=r['native_value'] or Decimal(native[r['source_column']])!=Decimal(r['value_decimal']) or native['unit']!=r['unit']:raise ValueError('National source row/value/unit differs')
            counts['national_cells_and_locators_matched']+=1
        counts['national_flagged_aggregate_discrepancies']=con.execute("SELECT count(*) FROM climate_records WHERE quality_flags LIKE '%published_total_differs_from_month_sum%'").fetchone()[0]
    base=ROOT/'data/processed/foundation/20260911T194849Z'
    for file in sorted(base.glob('forecast-*.json')):
        sample=json.loads(file.read_text());meta=sample['provenance'];body=(ROOT/'data/runtime'/meta['blob']).read_bytes()
        if hashlib.sha256(body).hexdigest()!=meta['sha256']:raise ValueError('Raw response changed')
        raw=json.loads(body);times=raw['hourly']['time'];point=sample['coverage']['requested_point']
        result=hourly(raw,meta,FORECAST,'weather_forecast','Open-Meteo GFS delivery; upstream run unspecified',point)
        if result['records']!=sample['records']:raise ValueError('Frozen normalized records differ from reparse')
        local=Counter()
        # Enumerate EVERY contiguous interval supported by this saved hourly axis.
        # Oracle reads raw array slices with Decimal; it does not use normalized locators.
        for parameter in FORECAST:
            values=raw['hourly'][parameter];records=[r for r in result['records'] if r['parameter']==parameter]
            for a in range(len(times)):
                for b in range(a+1,len(times)+1):
                    start=datetime.fromtimestamp(times[a],timezone.utc)
                    end=datetime.fromtimestamp(times[b-1]+3600,timezone.utc)
                    if parameter=='precipitation':start-=timedelta(hours=1);end-=timedelta(hours=1)
                    answer=calculate(records,parameter,start,end);native=values[a:b]
                    if any(v is None for v in native):
                        if answer['coverage']!='partial':raise ValueError('Missing value was hidden')
                    else:
                        ds=[Decimal(str(v)) for v in native]
                        if answer['coverage']!='complete':raise ValueError('Complete source interval rejected')
                        if parameter=='precipitation':
                            if Decimal(answer['value_decimal'])!=sum(ds,Decimal(0)):raise ValueError('Rain total differs from source oracle')
                        elif (Decimal(answer['min_decimal']),Decimal(answer['max_decimal']))!=(min(ds),max(ds)):raise ValueError('Hourly sample range differs from source oracle')
                    local['exact_interval_oracles']+=1
            # Every adjacent half-hour rain window must explicitly refuse splitting.
            if parameter=='precipitation':
                for a in range(len(times)-1):
                    start=datetime.fromtimestamp(times[a],timezone.utc)+timedelta(minutes=30)
                    answer=calculate(records,parameter,start,start+timedelta(hours=1))
                    if answer['coverage']!='partial' or answer['value_decimal'] is not None:raise ValueError('Fractional rain invented')
                    local['half_hour_rejections']+=1
            # Permuting input record order must not change calculations or provenance order.
            start=datetime.fromtimestamp(times[2],timezone.utc);end=start+timedelta(hours=3)
            if calculate(records,parameter,start,end)!=calculate(list(reversed(records)),parameter,start,end):raise ValueError('Input ordering changes answer')
            local['order_invariance_checks']+=1
        counts.update(local);counts['saved_land_locations']+=1;per_source[file.stem]=dict(local)
        print(json.dumps({'completed':file.stem,**dict(local)}),flush=True)
    summary={'status':'PASS','counts':dict(counts),'per_source':per_source,'real_provider_calls':0,
             'scope':'All registered asset bytes, all national cells, every contiguous interval in all six saved land forecast arrays. Historical replay; not current weather or scientific forecast skill.',
             'limitations':['The interval cases are data-driven oracle checks, not additional unittest methods.','Stored sample geography is six points; this does not establish nationwide live reliability.','Native national aggregate discrepancies are retained.']}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);print(json.dumps(run(p.parse_args().output),indent=2))
