"""Indexed GeoNames India snapshot; source place points, never LGD crosswalks."""
import csv,hashlib,io,json,sqlite3,unicodedata,zipfile,os,tempfile
from pathlib import Path
from datetime import datetime,timezone
from .answers import ROOT
from .geography import point

DEFAULT=ROOT/'data/processed/geography/geonames-india-20260912/places.sqlite'

def norm(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',value).casefold() if not unicodedata.combining(c)).split())


def choose_by_probe(candidates, probe, limit=8, score=None):
    """The candidate the connected product answers best for, and what was tried.

    Several Indian place names are shared by a city and a handful of villages, and the gazetteer
    has no population or seat rank that separates them (all five Kochis are PPL). Where a product
    can decide - a wave cell exists only near the coast, a station layer only reports near a city
    - asking the reader is worse than asking the product, as long as the choice, the measure and
    the alternatives are disclosed. `score` turns a probe answer into a comparable value and the
    smallest wins (a station 8 km away beats one 118 km away); without it the first answer wins.
    A probe that raises or returns nothing is recorded with its reason, and nothing is substituted
    silently.
    """
    tried = []
    best = None
    for candidate in list(candidates or [])[:limit]:
        coordinates = candidate.get('coordinates') or {}
        if coordinates.get('latitude') is None or coordinates.get('longitude') is None:
            continue
        try:
            answer = probe(candidate, coordinates)
        except Exception as failure:  # the product's own refusal is evidence, not an error to raise
            tried.append({'label': candidate.get('label'), 'why': str(failure)[:160]})
            continue
        if not answer:
            tried.append({'label': candidate.get('label'), 'why': 'the product returned nothing for this point'})
            continue
        if score is None:
            return candidate, tried, answer
        try:
            value = score(answer)
        except (TypeError, ValueError, KeyError):
            value = None
        if value is None:
            tried.append({'label': candidate.get('label'), 'why': 'the product answered without a comparable measure'})
            continue
        tried.append({'label': candidate.get('label'), 'why': 'answered at ' + str(value)})
        if best is None or value < best[0]:
            best = (value, candidate, answer)
    if best is not None:
        return best[1], tried, best[2]
    return None, tried, None
SEAT_ORDER={'PPLC':0,'PPLA':1,'PPLA2':2,'PPLA3':3,'PPLA4':4,'PPLA5':5,'PPLX':6,'PPL':7}


def feature_rank(feature):
    """Administrative seats first: a district or state seat outranks a village of the same name."""
    return SEAT_ORDER.get(str(feature or '').upper(),8)


def rank_matches(matches):
    """Stable order for candidates: seat order, then a canonical name, then the catalogue id."""
    return sorted(matches,key=lambda match:(feature_rank(match.get('feature')),
                                            0 if match.get('name_match_basis')=='canonical' else 1,
                                            str(match.get('id'))))


def preferred_match(matches):
    """(chosen, reason) when one administrative seat outranks the places sharing the name.

    This never substitutes a different place: the chosen entry carries the requested name and
    sits inside the state the caller supplied. It answers the common case where a user writes
    "Patna, Bihar" and four villages share the name with the district seat, and it still asks
    when the candidates are of the same order with nothing to tell them apart.
    """
    ranked=rank_matches(matches)
    if not ranked:return None,'no match'
    if len(ranked)==1:return ranked[0],'the only place with this name under the supplied filters'
    best=feature_rank(ranked[0].get('feature'))
    if best<=2 and feature_rank(ranked[1].get('feature'))>best:
        return ranked[0],'the only administrative seat among the places that share this name'
    # GeoNames India marks a district by the town it is named for. When exactly one candidate
    # sits in the district of its own name, that town is the one a person means by it; the
    # villages sharing the name sit in districts that carry other names.
    import difflib
    target=norm(ranked[0].get('name') or '')
    def district_carries_the_name(match):
        district=norm(match.get('admin2') or '')
        if not district or not target:return False
        return district==target or difflib.SequenceMatcher(None,district,target).ratio()>=0.82
    same_district=[match for match in ranked if district_carries_the_name(match)]
    if len(same_district)==1:
        return same_district[0],'its district carries the same name, and no other place that shares this name does'
    return None,'more than one place shares this name at the same order'

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

    @staticmethod
    def feature_rank(feature):
        return feature_rank(feature)

    @classmethod
    def rank_matches(cls,matches):
        return rank_matches(matches)

    @classmethod
    def preferred(cls,matches):
        return preferred_match(matches)

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
            state_names=sorted({row[0] for row in con.execute('SELECT DISTINCT admin1 FROM places') if row[0]})
        finally:con.close()
        def same(a,b):
            a=norm(a).replace(' district','').removeprefix('district ');b=norm(b).replace(' district','').removeprefix('district ')
            return a==b or a=='state of '+b or b=='state of '+a
        state_basis=''
        if state:
            wanted_state=state
            if rows and not any(same(r['admin1'],state) for r in rows):
                # A misspelt state name emptied a candidate list the place itself matched:
                # measured on 15 September 2026, "Ahmedbad, Gujrat" was refused although the
                # city matched. The state is resolved against the indexed names, bounded and
                # disclosed, and it is never guessed into a different state.
                import difflib
                def bare(value):return norm(value).removeprefix('state of ').strip()
                scored=sorted(((difflib.SequenceMatcher(None,bare(candidate),bare(state)).ratio(),candidate)
                               for candidate in state_names),reverse=True)
                if scored and scored[0][0]>=0.85 and (len(scored)==1 or scored[1][0]<scored[0][0]-0.05):
                    wanted_state=scored[0][1]
                    state_basis=('the state was read as '+str(scored[0][1])+' in the indexed catalogue, the closest name to '+str(state))
            against_state=[r for r in rows if same(r['admin1'],wanted_state)]
            if not against_state and state and not str(state).isascii():
                # A native-script state name cannot be compared with the catalogue's Latin
                # admin1 field. Measured live on 15 September 2026: the Devanagari question
                # found the place and the state filter then emptied the list. The name alone
                # resolves and the state is disclosed as unused rather than silently dropped.
                against_state = rows
                state_basis = ('the state was given in another script and was not used to filter: '
                               'the name alone resolved')
            rows = against_state
        if district:rows=[r for r in rows if same(r['admin2'],district)]
        rows=list({r['id']:r for r in rows}.values())
        canonical=[r for r in rows if norm(r['name'])==norm(name)]
        alias_alternatives=len(rows)-len(canonical) if canonical else 0
        if canonical and not approximate:rows=canonical
        if approximate:rows=rows[:20]
        return [{**r,'name_match_basis':'canonical' if norm(r['name'])==norm(name) else 'alias_or_approximate',
                 'state_match_basis':state_basis,'other_alias_matches':alias_alternatives,'match_type':'approximate_name_requires_confirmation' if approximate else 'source_name_or_alias','selection_id':'geonames:'+r['id'],'label':r['name']+', '+r['admin2']+', '+r['admin1'],
                 'coordinates':{'latitude':r['latitude'],'longitude':r['longitude']},'source_id':'S61',
                 'citation':{'source_id':'S61','url':'https://www.geonames.org/'+r['id'],'provider':'GeoNames','product':'India place catalogue','sha256':meta['archive_sha256'],'retrieved_at_utc':meta['retrieved_at_utc']},
                 'administrative_mapping':meta['administrative_mapping']} for r in rows]
