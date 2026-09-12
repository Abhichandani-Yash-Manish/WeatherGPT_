"""Local research index of all supplied historical district series; no boundary harmonisation."""
import csv,json,sqlite3,hashlib,io,tempfile,shutil
from decimal import Decimal
from pathlib import Path
from .climate import ROOT
from .transport import write_json,digest,utcnow,stamp,SourceError
FIELDS=[m+'_mm' for m in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec','annual','jf','mam','jjas','ond']]

def build():
    files=sorted((ROOT/'data/raw/imports/2026-09-11/states').glob('*.csv'))
    if len(files)!=32:raise SourceError('Expected the 32 registered district files')
    registered={a['path']:a['sha256'] for a in json.loads((ROOT/'data/registry/assets.json').read_text())['files']}
    inputs=[]
    for f in files:
        path=str(f.relative_to(ROOT));hash_=digest(f.read_bytes())
        if registered.get(path)!=hash_:raise SourceError('District input hash mismatch')
        inputs.append({'source_id':'S27','path':path,'sha256':hash_})
    code_hash=digest(Path(__file__).read_bytes());run='district-v1-'+digest(json.dumps([inputs,code_hash],sort_keys=True).encode())[:16]
    parent=ROOT/'data/processed/districts';out=parent/run
    if out.exists():
        m=json.loads((out/'build-manifest.json').read_text())
        for p,h in m['outputs'].items():
            if digest((out/p).read_bytes())!=h:raise SourceError('Modified district output')
        return out
    parent.mkdir(parents=True,exist_ok=True);tmp=Path(tempfile.mkdtemp(dir=parent,prefix='.building-'))
    count=0;missing=0;series={}
    try:
        with sqlite3.connect(tmp/'districts.sqlite') as con:
            con.execute('CREATE TABLE rainfall (series_id TEXT,year INTEGER,state TEXT,district TEXT,source_row INTEGER,source_file TEXT,asset_sha256 TEXT,payload TEXT,PRIMARY KEY(series_id,year))')
            for item in inputs:
                rows=csv.DictReader(io.StringIO((ROOT/item['path']).read_text(encoding='utf-8-sig')))
                if not set(FIELDS+['series_id','year','state_source','district_source','quality_flags','source_page'])<=set(rows.fieldnames or []):raise SourceError('District schema changed')
                for i,row in enumerate(rows,2):
                    if None in row or any(v is None for v in row.values()):raise SourceError('Ragged district row')
                    for field in FIELDS:
                        if row[field]=='':
                            if field in FIELDS[:12]:missing+=1
                            continue
                        val=Decimal(row[field])
                        if not val.is_finite() or val<0:raise SourceError('Invalid district rainfall value')
                    sid=row['series_id'];key=(row['state_source'],row['district_source'])
                    if sid in series and series[sid]!=key:raise SourceError('Series identity collision')
                    series[sid]=key
                    con.execute('INSERT INTO rainfall VALUES (?,?,?,?,?,?,?,?)',(sid,int(row['year']),*key,i,item['path'],item['sha256'],json.dumps(row)))
                    count+=1
            con.execute('CREATE INDEX by_place_year ON rainfall (state,district,year)')
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise SourceError('District SQLite integrity failed')
        audit={'rows':count,'series':len(series),'files':len(inputs),'missing_month_cells':missing,'total_measure_cells_including_missing':count*17,'source_transcription_verified_series':['IMD110-P611'],'scope':'Historical source districts, not modern boundary-harmonised districts.','release_status':'restricted_source_permission_unresolved','quality_note':'Original quality_flags and blank cells retained; original publication verification currently covers Ahmedabad only.'}
        if (count,len(series),missing)!=(60568,640,15817):raise SourceError('Unexpected frozen district snapshot counts')
        write_json(tmp/'audit.json',audit)
        write_json(tmp/'build-manifest.json',{'run_id':run,'built_at_utc':stamp(utcnow()),'implementation_sha256':code_hash,'inputs':inputs,'outputs':{p.name:digest(p.read_bytes()) for p in tmp.iterdir() if p.is_file()}})
        tmp.rename(out)
    except Exception:shutil.rmtree(tmp);raise
    return out

def lookup(database,state,district,year,period='annual'):
    field=period.lower()+'_mm'
    if field not in FIELDS:raise SourceError('Use a month abbreviation, annual, jf, mam, jjas or ond')
    with sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        rows=con.execute('SELECT * FROM rainfall WHERE lower(state)=lower(?) AND lower(district)=lower(?) AND year=?',(state.strip(),district.strip(),year)).fetchall()
    if len(rows)!=1:raise SourceError('No unique source district/year match; do not infer or fill missing years')
    r=dict(rows[0]);payload=json.loads(r.pop('payload'));native=payload[field]
    return {'status':'ok' if native else 'no_data','source_id':'S27','state':r['state'],'district':r['district'],'year':year,'period':period,'value_decimal':str(Decimal(native)) if native else None,'native_value':native,'unit':'mm','quality_flags':payload['quality_flags'].split(';') if payload['quality_flags'] else [],'provenance':{**r,'column':field,'original_publication_page':payload['source_page']},'source_transcription':'matched_1870_cells' if r['series_id']=='IMD110-P611' else 'not_yet_reconciled_against_original','limitations':['Historical source geography; modern district compatibility and homogeneity unresolved.','Local research use; original publication restricts redistribution.']}
