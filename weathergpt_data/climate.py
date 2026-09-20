"""Lossless normalisation and deterministic lookup for the frozen S25/S26 tables."""
import csv
import hashlib
import io
import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'national-climate-v1'
MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
SEASONS = {
    'Winter Season Jan-Feb': ('JF', [0,1]),
    'Pre-Monsoon Season Mar-May': ('MAM', [2,3,4]),
    'Monsoon Season Jun-Sep': ('JJAS', [5,6,7,8]),
    'Post-Monsoon Season Oct-Dec': ('OND', [9,10,11]),
}
METADATA = ['unit','geography','source_id','source_url','fetched_at_utc']
CONFIG = {
    'S25': {'filename':'rainfall.csv','parameter':'precipitation_amount','unit':'mm','native_id':'historical_rain_whi','url':'https://dsp.imdpune.gov.in/home_ogd_rainfall.php'},
    'S26': {'filename':'temperature.csv','parameter':'mean_temperature','unit':'degC','native_id':'historical_temp','url':'https://dsp.imdpune.gov.in/home_ogd_temp.php'},
}
PERIODS = {m: ('month', f'M{i+1:02d}', [i]) for i,m in enumerate(MONTHS)}
PERIODS.update({name: ('season', code, months) for name,(code,months) in SEASONS.items()})
PERIODS['Annual'] = ('year','ANNUAL',list(range(12)))
FIELDS = ['record_id','source_id','source_series_id','geography_id','geography_label','parameter','year','period_type','period_code','period_start','period_end_exclusive','value_decimal','native_value','unit','quality_flags','asset_sha256','raw_asset_path','source_row','source_column','source_url','retrieved_at_utc','transformation_version']


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n'


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def number(token, parameter):
    if token == '':
        return None
    try:
        value=Decimal(token)
    except InvalidOperation as exc:
        raise ValueError(f'Invalid numeric token: {token!r}') from exc
    if not value.is_finite():
        raise ValueError(f'Non-finite numeric token: {token!r}')
    if parameter == 'precipitation_amount' and value < 0:
        raise ValueError('Rainfall cannot be negative')
    return value


def normalise(payload, source_id, raw_path):
    """Return exact decimal strings and separate reconciliation records; never repair source totals."""
    cfg=CONFIG[source_id]
    reader=csv.DictReader(io.StringIO(payload.decode('utf-8-sig'), newline=''))
    expected={'Year', *PERIODS, *METADATA}
    if reader.fieldnames is None or len(reader.fieldnames)!=len(expected) or set(reader.fieldnames)!=expected:
        raise ValueError(f'{source_id}: unexpected CSV schema')
    records=[]; reconciliations=[]; years=set(); digest=sha(payload)
    for source_row,row in enumerate(reader,2):
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f'{source_id}: ragged CSV row {source_row}')
        year=int(row['Year'])
        if year in years: raise ValueError(f'{source_id}: duplicate year {year}')
        years.add(year)
        if row['unit'] != cfg['unit'] or row['geography'] != 'All India aggregate':
            raise ValueError(f'{source_id}: incompatible unit/geography on row {source_row}')
        if row['source_id'] != cfg['native_id'] or row['source_url'] != cfg['url']:
            raise ValueError(f'{source_id}: source metadata mismatch')
        fetched=datetime.fromisoformat(row['fetched_at_utc'])
        if fetched.tzinfo is None or fetched.utcoffset().total_seconds()!=0:
            raise ValueError('Retrieval timestamp must be timezone-aware UTC')
        values={col:number(row[col],cfg['parameter']) for col in PERIODS}
        flags={col:(['source_value_missing'] if values[col] is None else []) for col in PERIODS}
        if source_id=='S25':
            for col,(kind,code,indices) in PERIODS.items():
                if kind=='month': continue
                monthly=[values[MONTHS[i]] for i in indices]
                complete=all(v is not None for v in monthly)
                computed=sum(monthly,Decimal(0)) if complete else None
                published=values[col]
                difference=published-computed if published is not None and computed is not None else None
                # This frozen rainfall table is published to tenths of a millimetre.
                bound=Decimal('0.05')*(len(indices)+1)
                if any(values[c] is not None and values[c].as_tuple().exponent < -1 for c in [col]+[MONTHS[i] for i in indices]):
                    raise ValueError('Rainfall precision changed; review rounding reconciliation rule')
                status='not_comparable' if difference is None else ('beyond_rounding_bound' if abs(difference)>bound else ('exact' if difference==0 else 'within_rounding_bound'))
                if not complete: flags[col].append('component_months_missing')
                if status=='beyond_rounding_bound': flags[col].append('published_total_differs_from_month_sum')
                reconciliations.append({'source_id':source_id,'year':year,'period_code':code,'published_value':str(published) if published is not None else None,'computed_month_sum':str(computed) if computed is not None else None,'difference_mm':str(difference) if difference is not None else None,'rounding_bound_mm':str(bound),'status':status,'source_row':source_row,'source_column':col,'asset_sha256':digest})
        for col,(kind,code,indices) in PERIODS.items():
            start_month=indices[0]+1; end_month=indices[-1]+2
            end_year=year+1 if end_month==13 else year
            end_month=1 if end_month==13 else end_month
            value=values[col]
            key=f'{source_id}|{digest}|{year}|{code}'
            records.append({'record_id':sha(key.encode()),'source_id':source_id,'source_series_id':cfg['native_id'],'geography_id':'all-india-aggregate','geography_label':row['geography'],'parameter':cfg['parameter'],'year':year,'period_type':kind,'period_code':code,'period_start':f'{year:04d}-{start_month:02d}-01','period_end_exclusive':f'{end_year:04d}-{end_month:02d}-01','value_decimal':str(value) if value is not None else None,'native_value':row[col],'unit':cfg['unit'],'quality_flags':flags[col],'asset_sha256':digest,'raw_asset_path':raw_path,'source_row':source_row,'source_column':col,'source_url':row['source_url'],'retrieved_at_utc':row['fetched_at_utc'],'transformation_version':VERSION})
    if not records: raise ValueError('Empty source table')
    return records,reconciliations


from .publications import verified_connection

def lookup(database, source_id, year, period='ANNUAL', geography='all-india'):
    if geography != 'all-india':
        raise ValueError('This pipeline contains All India aggregates only; no district or station answer is supported.')
    if source_id not in CONFIG: raise ValueError('Supported sources are S25 rainfall and S26 mean temperature')
    if period not in {v[1] for v in PERIODS.values()}: raise ValueError('Unknown period; use ANNUAL, M01–M12, JF, MAM, JJAS or OND')
    path=Path(database).resolve()
    with verified_connection(path) as con:
        con.row_factory=sqlite3.Row
        row=con.execute('SELECT * FROM climate_records WHERE source_id=? AND year=? AND period_code=? AND geography_id=?',(source_id,year,period,'all-india-aggregate')).fetchone()
        if row is None: raise ValueError('No published value for that year/period in this snapshot (1901–2024).')
        record=dict(row);record['quality_flags']=json.loads(record['quality_flags'])
        check=con.execute('SELECT payload FROM reconciliation WHERE source_id=? AND year=? AND period_code=?',(source_id,year,period)).fetchone()
        reconciliation=json.loads(check[0]) if check else None
    return {'status':'value_missing' if record['value_decimal'] is None else 'ok','scope':'Published historical All India aggregate; not current or district weather.','record':record,'reconciliation':reconciliation,'citation':{'source_id':source_id,'url':record['source_url'],'raw_asset_path':record['raw_asset_path'],'sha256':record['asset_sha256'],'row':record['source_row'],'column':record['source_column']}}


def build(root=ROOT, output_root=None):
    root=Path(root)
    registry=json.loads((root/'data/registry/sources.json').read_text())
    sources={s['id']:s for s in registry['products']}
    asset_manifest=json.loads((root/'data/registry/assets.json').read_text())
    assets={a['path']:a for a in asset_manifest['files']}
    inputs=[];records=[];checks=[]
    for sid,cfg in CONFIG.items():
        paths=[p for p in sources[sid]['evidence_files'] if p.endswith('/'+cfg['filename'])]
        if len(paths)!=1: raise ValueError(f'{sid}: expected exactly one CSV evidence asset')
        path=paths[0];payload=(root/path).read_bytes()
        if path not in assets or sha(payload)!=assets[path]['sha256']:
            raise ValueError(f'{sid}: raw source integrity mismatch')
        rows,reconciliations=normalise(payload,sid,path)
        if {r['year'] for r in rows} != set(range(1901,2025)) or len(rows)!=124*17:
            raise ValueError(f'{sid}: frozen snapshot coverage changed; review contract')
        records.extend(rows);checks.extend(reconciliations)
        inputs.append({'source_id':sid,'path':path,'sha256':sha(payload),'published_years':124,'normalised_records':len(rows)})
    # Content-address inputs AND implementation; reruns cannot silently replace another revision.
    code_sha=sha(Path(__file__).read_bytes())
    run_id=VERSION+'-'+sha(dump({'inputs':inputs,'implementation_sha256':code_sha}).encode())[:16]
    parent=Path(output_root) if output_root else root/'data/processed/climate'
    out=parent/run_id
    if out.exists():
        manifest=json.loads((out/'build-manifest.json').read_text())
        for name,digest in manifest['outputs'].items():
            if sha((out/name).read_bytes())!=digest: raise ValueError(f'Processed output was modified: {name}')
        return out
    parent.mkdir(parents=True,exist_ok=True)
    import tempfile
    import shutil
    temp=Path(tempfile.mkdtemp(prefix='.building-',dir=parent))
    try:
        with (temp/'records.jsonl').open('w') as stream:
            for r in records: stream.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
        with (temp/'records.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=FIELDS,lineterminator='\n');writer.writeheader()
            for r in records: writer.writerow({**r,'quality_flags':json.dumps(r['quality_flags'])})
        (temp/'reconciliation.json').write_text(dump(checks))
        with sqlite3.connect(temp/'climate.sqlite') as con:
            schema=','.join(f'{f} '+('INTEGER' if f in ['year','source_row'] else 'TEXT') for f in FIELDS)
            con.execute(f'CREATE TABLE climate_records ({schema}, PRIMARY KEY(record_id), UNIQUE(source_id,geography_id,year,period_code))')
            con.executemany('INSERT INTO climate_records VALUES ('+','.join('?' for _ in FIELDS)+')',[[json.dumps(r[f]) if f=='quality_flags' else r[f] for f in FIELDS] for r in records])
            con.execute('CREATE TABLE reconciliation (source_id TEXT,year INTEGER,period_code TEXT,payload TEXT,PRIMARY KEY(source_id,year,period_code))')
            con.executemany('INSERT INTO reconciliation VALUES (?,?,?,?)',[(c['source_id'],c['year'],c['period_code'],json.dumps(c)) for c in checks])
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('SQLite integrity failed')
        # Independently round-trip each measure to its original CSV cell.
        original={i['source_id']:list(csv.DictReader(io.StringIO((root/i['path']).read_text()))) for i in inputs}
        for r in records:
            cell=original[r['source_id']][r['source_row']-2][r['source_column']]
            if cell != r['native_value'] or (str(Decimal(cell)) if cell else None)!=r['value_decimal']:
                raise ValueError('Source round-trip failed')
        audit={'record_count':len(records),'records_per_source':{sid:sum(r['source_id']==sid for r in records) for sid in CONFIG},'years':[1901,2024],'grain':'source × All India × year × distinct month/season/annual period','missing_values':sum(r['value_decimal'] is None for r in records),'round_trip_cells_checked':len(records),'unique_record_ids':len({r['record_id'] for r in records}),'rainfall_reconciliations':len(checks),'rainfall_totals_beyond_rounding_bound':[c for c in checks if c['status']=='beyond_rounding_bound'],'limitations':['Monthly, seasonal and annual periods overlap; never sum across period types.','Source table match is not a scientific homogeneity assessment.','Historical national aggregates cannot answer district weather or daily dry spells.']}
        (temp/'audit.json').write_text(dump(audit))
        # The staged database must pass the same verified read path as serving data.
        (temp/'build-manifest.json').write_text(dump({'outputs':{'climate.sqlite':sha((temp/'climate.sqlite').read_bytes())}}))
        example=lookup(temp/'climate.sqlite','S25',2024)
        (temp/'build-manifest.json').unlink()  # Final manifest below covers all outputs.
        (temp/'example-answer.json').write_text(dump(example))
        r=example['record'];c=example['reconciliation']
        (temp/'example-answer.md').write_text(f"# First reproducible WeatherGPT answer\n\n**Question:** What was India's annual rainfall in 2024?\n\nThe supplied IMD All India table reports **{r['value_decimal']} mm** for 2024. This is a national historical aggregate.\n\nIts twelve published months sum to **{c['computed_month_sum']} mm**, a difference of **{c['difference_mm']} mm** from the published annual total. The pipeline preserves the published total and flags the discrepancy; it does not silently repair it.\n\nSource: [IMD rainfall table]({r['source_url']}), S25, CSV row {r['source_row']}, column `{r['source_column']}`. See `example-answer.json` for the exact source path and hash.\n")
        outputs={p.name:sha(p.read_bytes()) for p in temp.iterdir() if p.is_file()}
        (temp/'build-manifest.json').write_text(dump({'run_id':run_id,'built_at_utc':datetime.now(timezone.utc).isoformat(),'transformation_version':VERSION,'implementation_sha256':code_sha,'inputs':inputs,'outputs':outputs,'note':'No network, LLM, inferred missing values or source-total repair.'}))
        temp.rename(out)
    except Exception:
        shutil.rmtree(temp)
        raise
    return out