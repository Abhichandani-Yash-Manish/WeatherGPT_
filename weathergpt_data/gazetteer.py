"""Indexed GeoNames India snapshot; source place points, never LGD crosswalks."""
import csv,hashlib,io,json,sqlite3,unicodedata,zipfile,os,tempfile
from pathlib import Path
from datetime import datetime,timezone
from .answers import ROOT
from .geography import point

DEFAULT=ROOT/'data/processed/geography/geonames-india-20260912/places.sqlite'

def norm(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',value).casefold() if not unicodedata.combining(c)).split())

def build(archive,output=DEFAULT):
    archive=Path(archive);output=Path(output)
    if output.exists():raise FileExistsError('Gazetteer output already exists')
    with zipfile.ZipFile(archive) as z:
        member=z.getinfo('IN.txt')
        if member.file_size>250_000_000:raise ValueError('Gazetteer exceeds size cap')
        body=z.read('IN.txt')
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.building-',suffix='.sqlite',dir=output.parent);os.close(fd)
    working=Path(temp)
    con=sqlite3.connect(working)
    try:
        con.executescript('CREATE TABLE places (id TEXT PRIMARY KEY,name TEXT,latitude REAL,longitude REAL,feature TEXT,admin1 TEXT,admin2 TEXT,modified TEXT); CREATE TABLE aliases (name TEXT,id TEXT,UNIQUE(name,id)); CREATE INDEX alias_name ON aliases(name); CREATE TABLE metadata (payload TEXT);')
        rows=list(csv.reader(io.StringIO(body.decode()),delimiter='\t'));admin1={};admin2={}
        for row in rows:
            if len(row)!=19 or row[8]!='IN':raise ValueError('Unexpected GeoNames schema/country')
            point(float(row[4]),float(row[5]))
            if row[7]=='ADM1':admin1[row[10]]=row[1]
            if row[7]=='ADM2':admin2[(row[10],row[11])]=row[1]
        settlements=0
        for row in rows:
            if row[6]!='P' or row[7] in {'PPLH','PPLQ','PPLW'}:continue
            con.execute('INSERT INTO places VALUES (?,?,?,?,?,?,?,?)',(row[0],row[1],float(row[4]),float(row[5]),row[7],admin1.get(row[10],row[10]),admin2.get((row[10],row[11]),row[11]),row[18]))
            names={norm(v) for v in [row[1],row[2]]+row[3].split(',') if v}
            con.executemany('INSERT OR IGNORE INTO aliases VALUES (?,?)',[(v,row[0]) for v in names]);settlements+=1
        meta={'source_id':'S61','url':'https://download.geonames.org/export/dump/IN.zip','archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'member_sha256':hashlib.sha256(body).hexdigest(),'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'records_in_extract':len(rows),'settlement_records':settlements,'alias_records':con.execute('SELECT count(*) FROM aliases').fetchone()[0],'license':'CC BY 4.0','attribution':'GeoNames','administrative_mapping':'GeoNames source labels; not reviewed LGD codes or boundaries'}
        con.execute('INSERT INTO metadata VALUES (?)',(json.dumps(meta),));con.commit()
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        con.close()
        os.link(working,output)  # Only a complete database is published; never overwrite.
        (output.parent/'manifest.json').write_text(json.dumps({**meta,'database_sha256':hashlib.sha256(output.read_bytes()).hexdigest()},indent=2)+'\n')
        return meta
    finally:
        con.close();working.unlink(missing_ok=True)

class Gazetteer:
    def __init__(self,path=DEFAULT):
        self.path=Path(path)
        manifest=json.loads((self.path.parent/'manifest.json').read_text())
        self.expected_sha256=manifest['database_sha256']
        if hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.expected_sha256:raise ValueError('Place catalogue integrity failed')
    def alternates(self,place_id,limit=200):
        """Every alias name recorded for one place, bounded. Source labels, not a crosswalk."""
        if hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.expected_sha256:raise ValueError('Place catalogue changed after verification')
        con=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)
        try:return [row[0] for row in con.execute('SELECT name FROM aliases WHERE id=? ORDER BY name LIMIT ?',(place_id,max(1,min(int(limit),500))))]
        finally:con.close()

    def search(self,name,state='',district=''):
        if hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.expected_sha256:raise ValueError('Place catalogue changed after verification')
        con=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
        try:
            rows=[dict(r) for r in con.execute('SELECT p.* FROM places p JOIN aliases a ON p.id=a.id WHERE a.name=? ORDER BY p.id',(norm(name),))]
            approximate=False
            if not rows and len(norm(name))>=4:
                import difflib
                possibilities=con.execute('SELECT DISTINCT p.*,a.name AS matched_alias FROM places p JOIN aliases a ON p.id=a.id WHERE a.name LIKE ? LIMIT 2500',(norm(name)[:3]+'%',)).fetchall()
                ranked=[]
                for row in possibilities:
                    r=dict(row);score=difflib.SequenceMatcher(None,norm(name),r.pop('matched_alias')).ratio()
                    if score>=0.78:ranked.append((score,r))
                ranked.sort(key=lambda item:-item[0]);rows=[r for _,r in ranked];approximate=True
            meta=json.loads(con.execute('SELECT payload FROM metadata').fetchone()[0])
        finally:con.close()
        def same(a,b):
            a=norm(a).replace(' district','').removeprefix('district ');b=norm(b).replace(' district','').removeprefix('district ')
            return a==b or a=='state of '+b or b=='state of '+a
        if state:rows=[r for r in rows if same(r['admin1'],state)]
        if district:rows=[r for r in rows if same(r['admin2'],district)]
        rows=list({r['id']:r for r in rows}.values())
        canonical=[r for r in rows if norm(r['name'])==norm(name)]
        alias_alternatives=len(rows)-len(canonical) if canonical else 0
        if canonical and not approximate:rows=canonical
        if approximate:rows=rows[:20]
        return [{**r,'name_match_basis':'canonical' if norm(r['name'])==norm(name) else 'alias_or_approximate','other_alias_matches':alias_alternatives,'match_type':'approximate_name_requires_confirmation' if approximate else 'source_name_or_alias','selection_id':'geonames:'+r['id'],'label':r['name']+', '+r['admin2']+', '+r['admin1'],
                 'coordinates':{'latitude':r['latitude'],'longitude':r['longitude']},'source_id':'S61',
                 'citation':{'source_id':'S61','url':'https://www.geonames.org/'+r['id'],'provider':'GeoNames','product':'India place catalogue','sha256':meta['archive_sha256'],'retrieved_at_utc':meta['retrieved_at_utc']},
                 'administrative_mapping':meta['administrative_mapping']} for r in rows]
