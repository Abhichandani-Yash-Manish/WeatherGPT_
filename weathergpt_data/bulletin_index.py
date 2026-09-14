"""Versioned, crop-bound source passages; PDF text is evidence, never instructions."""
import hashlib,io,json,math,re,sqlite3,threading
from datetime import date,datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from .transport import SourceError,digest,parsed,stamp
from .gazetteer import norm
from .foundation import ROOT
from .documents import strip_controls

MODEL='intfloat/multilingual-e5-small'
REVISION='614241f622f53c4eeff9890bdc4f31cfecc418b3'
EXTRACTION_VERSION='bulletin-grid-v2'
LOCK=threading.RLock();_MODEL=None
ALIASES={'paddy':'rice','dhan':'rice','धान':'rice','kapas':'cotton','कपास':'cotton','કપાસ':'cotton','makka':'maize','मक्का':'maize','haldi':'turmeric','हल्दी':'turmeric','mungfali':'groundnut','peanut':'groundnut','moong':'green gram','urad':'black gram','arhar':'pigeon pea','bajra':'pearl millet','baingan':'brinjal'}
def crop_name(value):
    value=norm(value);return ALIASES.get(value,value)
def clean(value):return ' '.join(strip_controls((value or '').replace('\uf0b7','•'))[0].split())


def embed(texts,query=False):
    global _MODEL
    with LOCK:
        if _MODEL is None:
            from sentence_transformers import SentenceTransformer
            import torch
            torch.set_num_threads(2)
            _MODEL=SentenceTransformer(MODEL,revision=REVISION,local_files_only=True,trust_remote_code=False,device='cpu')
        return _MODEL.encode([('query: ' if query else 'passage: ')+t for t in texts],normalize_embeddings=True,show_progress_bar=False).tolist()


def metadata(pages,state,district,now,forecast_cells=None):
    text=clean(pages[0]);low=norm(text)
    district_patterns=[r'Agromet Advisory Bulletin for (?:the )?'+re.escape(district)+r' District',re.escape(district)+r' district agromet advisory bulletin']
    if not any(re.search(p,text,re.I) for p in district_patterns):raise SourceError('Printed district could not be verified with the supported layout rules; the layout may be unsupported or the selected district may differ')
    if norm(state) not in low:raise SourceError('Printed state could not be verified')
    if 'gramin krishi mausam sewa' not in low and 'india meteorological department' not in low:raise SourceError('Unrecognized bulletin issuer/family')
    m=re.search(r'(?:Issued [Oo]n\s*:?|Date\s*:\s*(?:[A-Za-z]+,\s*)?)(\d{4}-\d{2}-\d{2}|\d{2}[-.]\d{2}[-.]\d{4})',text)
    if not m:raise SourceError('Printed issue date could not be resolved')
    raw=m[1];issue=datetime.strptime(raw,'%Y-%m-%d' if len(raw.split('-')[0])==4 else '%d-%m-%Y' if '-' in raw else '%d.%m.%Y').date()
    if issue>now.astimezone(ZoneInfo('Asia/Kolkata')).date():raise SourceError('Bulletin issue date is in the future')
    # Use only the forecast heading/table, excluding past-weather dates and ERF.
    dates=[]
    heading=re.search(r'(?:Parameters/\s*Date|Parameter\s+)(.{0,250})',text)
    if heading:
        for raw in re.findall(r'\b(?:\d{4}-\d{2}-\d{2}|\d{2}[-.]\d{2}[-.]\d{4})\b',heading[1]):
            try:dates.append(datetime.strptime(raw,'%Y-%m-%d' if raw[:4].isdigit() and raw[4]=='-' else '%d-%m-%Y' if '-' in raw else '%d.%m.%Y').date())
            except ValueError:pass
    if forecast_cells:
        dates=[date.fromisoformat(re.sub(r'\s+','',c)) for c in forecast_cells]
    span=re.search(r'From\s+(\d+)(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})\s+to\s+(\d+)(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})',text,re.I)
    if span:
        a=datetime.strptime(' '.join(span.group(1,2,3)),'%d %B %Y').date();b=datetime.strptime(' '.join(span.group(4,5,6)),'%d %B %Y').date();dates=[a+timedelta(days=i) for i in range((b-a).days+1)]
    dates=sorted(set(d for d in dates if issue<=d<=issue+timedelta(days=7)))
    if len(dates)!=5 or any(b-a!=timedelta(days=1) for a,b in zip(dates,dates[1:])):raise SourceError('The five-day forecast context could not be verified')
    family='arnej_grid' if 'anand agricultural university' in low else 'tnau_grid' if 'tamil nadu agricultural university' in low else 'gkms_grid'
    return {'state':state,'district':district,'issue_date':issue.isoformat(),'forecast_start':dates[0].isoformat(),'forecast_end':dates[-1].isoformat(),'advice_valid_until':None,'family':family,'issuer_context':text[:min(650,text.find('Medium range') if 'Medium range' in text else 650)],'language':'en'}


def extract(body,state,district,now):
    import pdfplumber
    with pdfplumber.open(io.BytesIO(body)) as pdf:
        if not 1<=len(pdf.pages)<=30:raise SourceError('Bulletin page count exceeds reviewed workload')
        pages=[p.extract_text() or '' for p in pdf.pages]
        forecast_cells=None
        for table in pdf.pages[0].extract_tables():
            if table and table[0] and clean(table[0][0])=='Parameter' and len(table[0])==6:
                forecast_cells=table[0][1:]
        meta=metadata(pages,state,district,now,forecast_cells)
        rows=[];previous=None
        for number,page in enumerate(pdf.pages[1:],2):
            if meta['family']=='arnej_grid':
                grid=[r for r in page.rects if r.get('non_stroking_color')==(0.122,0.306,0.475)]
                x=sorted(set(round((r['x0']+r['x1'])/2,1) for r in grid if r['width']<=3 and r['height']>20));ys=sorted(set(round((r['top']+r['bottom'])/2,1) for r in grid if r['height']<=3 and r['width']>300))
                if len(x)!=4:continue
                for row,(a,b) in enumerate(zip(ys,ys[1:])):
                    cells=[clean(page.crop((l+1,a+1,r-1,b-1)).extract_text()) for l,r in zip(x,x[1:])]
                    crop,stage,text=cells
                    if crop in {'Field Crops','Fruit Crop','Livestock'} or text=='Advisory':previous=None;continue
                    if crop=='General advice':stage='';text=clean(page.crop((x[1]+1,a+1,x[-1]-1,b-1)).extract_text())
                    if not crop and previous:crop,stage=previous
                    elif not crop or len(crop)>60 or not re.fullmatch(r'[A-Za-z ,/()-]+',crop):previous=None;continue
                    if not text or len(text)<20:continue
                    previous=(crop,stage);rows.append({'page':number,'row':row+1,'crop':crop,'stage':stage,'text':text,'bbox':[x[0],a,x[-1],b]})
            else:
                for ti,table in enumerate(page.find_tables()):
                    for ri,cells in enumerate(table.extract()):
                        if len(cells)==3:
                            crop,stage,text=map(clean,cells)
                            if not crop or crop.lower() in {'crop','general'} and text.lower()=='advisory':continue
                        elif len(cells)==2:
                            crop,text=map(clean,cells);stage=''
                            if not crop and text:raise SourceError('Unbound advisory text crosses a page/table boundary; this document needs layout review before serving')
                            if crop.count('(')>1:raise SourceError('Compound crop aliases and growth-stage headings need reviewed separation before serving')
                            if not crop or 'specific advisory' in text.lower() or len(crop)>100:continue
                            m=re.fullmatch(r'(.+?)\s*\((.+)\)',crop)
                            if m:crop,stage=m[1],m[2]
                        else:continue
                        if not text or len(text)<25 or not re.fullmatch(r'[A-Za-z ,/()-]+',crop):continue
                        rows.append({'page':number,'row':ri+1,'table':ti+1,'crop':crop,'stage':stage,'text':text,'bbox':list(table.rows[ri].bbox)})
        if not rows:raise SourceError('No crop/stage rows matched the reviewed extraction families')
    chunks=[];quarantines=[];sha=digest(body)
    crop_keys={crop_name(r['crop']) for r in rows}-{'general','general advice','animals','chicken'}
    for row in rows:
        parts=[clean(p) for p in row['text'].split('•') if clean(p)]
        for part in parts:
            if len(part)>4000:raise SourceError('A source passage exceeds bounded retrieval size; splitting needs review')
            mentioned={c for c in crop_keys if re.search(r'(?<!\w)'+re.escape(c)+r'(?!\w)',norm(part))}
            if crop_name(row['crop']) in crop_keys and mentioned and crop_name(row['crop']) not in mentioned:
                quarantines.append({**row,'text':part,'reason':'Body names another crop but not its row crop; source association needs review'});continue
            chunk={**row,'text':part,'crop_key':crop_name(row['crop']),'source_id':'S57','document_sha256':sha,'extraction_version':EXTRACTION_VERSION}
            chunk['id']=digest(json.dumps(chunk,sort_keys=True).encode());chunks.append(chunk)
    return {**meta,'sha256':sha,'pages':len(pages),'chunks':chunks,'quarantined_passages':quarantines,'extraction_version':EXTRACTION_VERSION,'extraction_status':'reviewed_family_rules','scope':'Published source passages; no personalized prescription or independent agronomic validation'}


class BulletinIndex:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as db:db.executescript('CREATE TABLE IF NOT EXISTS documents (sha TEXT PRIMARY KEY,payload TEXT,payload_hash TEXT);CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY,document_sha TEXT,payload TEXT,payload_hash TEXT,embedding TEXT,embedding_hash TEXT,model_revision TEXT);CREATE TABLE IF NOT EXISTS passages (id TEXT PRIMARY KEY,document_sha TEXT,family TEXT,scope TEXT,region TEXT,payload TEXT,payload_hash TEXT,embedding TEXT,embedding_hash TEXT,model_revision TEXT);CREATE INDEX IF NOT EXISTS passages_family ON passages(family,scope,region);CREATE TABLE IF NOT EXISTS heads (region TEXT PRIMARY KEY,sha TEXT,checked_at TEXT,status TEXT,error TEXT);')
    def connection(self):return sqlite3.connect(self.path,timeout=10)
    def publish(self,document,provenance,checked_at,encoder=embed):
        chunks=document['chunks'];vectors=encoder([c['crop']+' '+c['stage']+' '+c['text'] for c in chunks]);assert len(vectors)==len(chunks)
        if any(not v or any(not math.isfinite(n) for n in v) for v in vectors):raise SourceError('Invalid document embedding')
        payload=json.dumps({**document,'provenance':provenance},sort_keys=True,ensure_ascii=False)
        from .transport import write_json
        manifest={'document':digest(payload.encode()),'chunks':{c['id']:{'payload':digest(json.dumps(c,sort_keys=True,ensure_ascii=False).encode()),'embedding':digest(json.dumps(v).encode())} for c,v in zip(chunks,vectors)}}
        target=self.path.parent/'publications'/(document['sha256']+'.json')
        if target.exists():
            if json.loads(target.read_text())!=manifest:raise SourceError('Immutable bulletin publication already differs')
        else:write_json(target,manifest)
        with self.connection() as db:
            db.execute('INSERT OR IGNORE INTO documents VALUES (?,?,?)',(document['sha256'],payload,digest(payload.encode())))
            for chunk,vector in zip(chunks,vectors):
                text=json.dumps(chunk,sort_keys=True,ensure_ascii=False);embedding=json.dumps(vector)
                db.execute('INSERT OR IGNORE INTO chunks VALUES (?,?,?,?,?,?,?)',(chunk['id'],document['sha256'],text,digest(text.encode()),embedding,digest(embedding.encode()),REVISION))
            db.execute('INSERT OR REPLACE INTO heads VALUES (?,?,?,?,?)',(norm(document['state']+'|'+document['district']),document['sha256'],checked_at,'ok',''))
    def head(self,state,district):
        with self.connection() as db:
            db.row_factory=sqlite3.Row;r=db.execute('SELECT * FROM heads WHERE region=?',(norm(state+'|'+district),)).fetchone()
        return dict(r) if r else None
    def mark_failed(self,state,district,checked_at,error):
        prior=self.head(state,district)
        with self.connection() as db:db.execute('INSERT OR REPLACE INTO heads VALUES (?,?,?,?,?)',(norm(state+'|'+district),(prior or {}).get('sha'),checked_at,'failed',error))
    def document(self,sha):
        with self.connection() as db:r=db.execute('SELECT payload,payload_hash FROM documents WHERE sha=?',(sha,)).fetchone()
        if not r or digest(r[0].encode())!=r[1]:raise SourceError('Published bulletin integrity failed')
        manifest=json.loads((self.path.parent/'publications'/(sha+'.json')).read_text())
        if manifest['document']!=r[1]:raise SourceError('Bulletin publication manifest mismatch')
        document=json.loads(r[0]);raw=Path(document['provenance']['raw_file']).resolve()
        if (self.path.parent/'raw').resolve() not in raw.parents:raise SourceError('Bulletin raw path leaves its evidence store')
        body=raw.read_bytes()
        if digest(body)!=sha or document['sha256']!=sha:raise SourceError('Bulletin raw source integrity failed')
        derived=extract(body,document['state'],document['district'],parsed(document['provenance']['retrieved_at_utc']))
        if any(document.get(k)!=v for k,v in derived.items()):raise SourceError('Bulletin content differs from raw PDF extraction')
        return document
    def document_body_of_chunk_publication(self,sha):
        """The raw body behind a chunk publication, or None when it has been pruned away."""
        document=self.document(sha)
        raw=Path(document['provenance']['raw_file'])
        return raw.read_bytes() if raw.exists() else None
    def search(self,state,district,query,crop='',stage='',topic='general',limit=3,encoder=embed):
        head=self.head(state,district)
        if not head or head['status']!='ok':raise SourceError('No healthy reviewed bulletin version for this district')
        doc=self.document(head['sha'])
        if norm(doc['state']+'|'+doc['district'])!=norm(state+'|'+district):raise SourceError('Bulletin region binding failed')
        manifest=json.loads((self.path.parent/'publications'/(head['sha']+'.json')).read_text())
        expected={c['id']:c for c in doc['chunks']}
        with self.connection() as db:rows=db.execute('SELECT payload,payload_hash,embedding,embedding_hash,model_revision FROM chunks WHERE document_sha=?',(head['sha'],)).fetchall()
        if len(rows)!=len(expected):raise SourceError('Incomplete bulletin index')
        candidates=[];requested=crop_name(crop)
        for payload,phash,encoded,ehash,revision in rows:
            if digest(payload.encode())!=phash or digest(encoded.encode())!=ehash or revision!=REVISION:raise SourceError('Bulletin chunk/embedding integrity failed')
            c=json.loads(payload)
            if c.get('id') not in expected or c!=expected[c['id']] or manifest['chunks'].get(c['id'])!={'payload':phash,'embedding':ehash}:raise SourceError('Published bulletin chunk binding failed')
            vector=json.loads(encoded)
            if not vector or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in vector):raise SourceError('Invalid stored embedding')
            if requested and c['crop_key']!=requested:continue
            if stage and norm(stage) not in norm(c['stage']):continue
            topic_words={'irrigation':r'irrigat|water log|waterlog|drain|moisture','sowing':r'sow|seed|nursery|land prepar','pest':r'pest|disease|insect|borer|rot|mite|whitefly|thrip|wilt|caterpillar|jassid|larva|fung','nutrition':r'fertiliz|fertilis|urea|nutrient|nitrogen|phosph|potash|manure','harvest':r'harvest|pick|matur|stor'}
            if topic!='general' and not re.search(topic_words[topic],c['text'],re.I):continue
            if topic=='irrigation' and re.search(topic_words['pest'],c['text'],re.I) and not re.search(r'(?:need based|provide|apply|withhold|avoid|give|maintain|schedule|postpone).{0,35}(?:irrigat|water)|drain(?:age| out| the)',c['text'],re.I):continue
            candidates.append((c,json.loads(encoded)))
        if not candidates:return doc,[],{'mode':'metadata_filtered','candidates':0,'requested_crop':crop,'requested_stage':stage}
        terms=set(re.findall(r'\w+',norm(query)));qvector=encoder([query],query=True)[0]
        tokens=[re.findall(r'\w+',norm(c['crop']+' '+c['stage']+' '+c['text'])) for c,v in candidates];avg=sum(map(len,tokens))/len(tokens)
        lex=[];dense=[]
        for i,((c,v),words) in enumerate(zip(candidates,tokens)):
            if len(v)!=len(qvector):raise SourceError('Embedding dimension mismatch')
            score=0.
            for term in terms:
                tf=words.count(term);df=sum(term in w for w in tokens);idf=math.log(1+(len(tokens)-df+.5)/(df+.5))
                score+=idf*tf*2.2/(tf+1.2*(.25+.75*len(words)/avg))
            lex.append((i,score));dense.append((i,sum(a*b for a,b in zip(qvector,v))))
        lex.sort(key=lambda p:(-p[1],candidates[p[0]][0]['id']));dense.sort(key=lambda p:(-p[1],candidates[p[0]][0]['id']))
        ranks={i:0. for i in range(len(candidates))}
        for ranked in [lex,dense]:
            for rank,(i,score) in enumerate(ranked,1):ranks[i]+=1/(60+rank)
        best=sorted(ranks,key=lambda i:(-ranks[i],candidates[i][0]['id']))[:limit]
        result=[{**candidates[i][0],'retrieval':{'rrf_score':ranks[i],'lexical_score':dict(lex)[i],'semantic_score':dict(dense)[i]}} for i in best]
        return doc,result,{'mode':'bm25_plus_multilingual_e5_rrf','candidates':len(candidates),'model':MODEL,'revision':REVISION,'metadata_filters':{'state':state,'district':district,'crop':crop,'stage':stage},'scores_are_confidence':False}

    def publish_document(self,document,provenance,checked_at,encoder=embed):
        """Index one whole document. Integrity is payload and embedding binding, not raw re-derivation."""
        passages=document['passages']
        if not passages:raise SourceError('A document without passages cannot be published')
        texts=[(p.get('family') or '')+' '+(p.get('text') or '') for p in passages]
        bad=[i for i,t in enumerate(texts) if not isinstance(t,str) or not t.strip() or any(ord(c)<9 for c in t)]
        if bad:raise SourceError('Passage text is not embeddable at indexes '+str(bad[:5])+' first value '+repr(texts[bad[0]])[:160])
        vectors=encoder(texts);assert len(vectors)==len(passages)
        if any(not v or any(not math.isfinite(n) for n in v) for v in vectors):raise SourceError('Invalid document embedding')
        payload=json.dumps({**document,'provenance':provenance},sort_keys=True,ensure_ascii=False)
        from .transport import write_json
        manifest={'document':digest(payload.encode()),'passages':{p['id']:{'payload':digest(json.dumps(p,sort_keys=True,ensure_ascii=False).encode()),'embedding':digest(json.dumps(v).encode())} for p,v in zip(passages,vectors)}}
        # Document publications keep their own namespace. The chunk-based bulletin path
        # publishes under publications/<sha>.json, and a district present in both corpora
        # would otherwise collide with its own other-shaped manifest.
        target=self.document_publication(document['sha256'])
        if target.exists():
            if json.loads(target.read_text())!=manifest:raise SourceError('Immutable document publication already differs')
        else:write_json(target,manifest)
        with self.connection() as db:
            existing=db.execute('SELECT payload_hash FROM documents WHERE sha=?',(document['sha256'],)).fetchone()
            db.execute('INSERT OR IGNORE INTO documents VALUES (?,?,?)',(document['sha256'],payload,digest(payload.encode())))
            for passage,vector in zip(passages,vectors):
                text=json.dumps(passage,sort_keys=True,ensure_ascii=False);embedding=json.dumps(vector)
                db.execute('INSERT OR IGNORE INTO passages VALUES (?,?,?,?,?,?,?,?,?,?)',(passage['id'],document['sha256'],passage['family'],passage['scope'],passage.get('region'),text,digest(text.encode()),embedding,digest(embedding.encode()),REVISION))
            db.execute('INSERT OR REPLACE INTO heads VALUES (?,?,?,?,?)',(self.document_key(document['family'],document.get('region')),document['sha256'],checked_at,'ok',''))
        return {'sha256':document['sha256'],'passages':len(passages),'duplicate':existing is not None}
    def document_publication(self,sha):return self.path.parent/'publications'/'documents'/(sha+'.json')
    @staticmethod
    def document_key(family,region):return 'document|'+str(family)+'|'+str(region or '-')
    def document_head(self,family,region=None):
        with self.connection() as db:
            db.row_factory=sqlite3.Row;r=db.execute('SELECT * FROM heads WHERE region=?',(self.document_key(family,region),)).fetchone()
        return dict(r) if r else None
    def mark_document_failed(self,family,region,checked_at,error):
        prior=self.document_head(family,region)
        with self.connection() as db:db.execute('INSERT OR REPLACE INTO heads VALUES (?,?,?,?,?)',(self.document_key(family,region),(prior or {}).get('sha'),checked_at,'failed',error))
    def passage_document(self,sha):
        with self.connection() as db:r=db.execute('SELECT payload,payload_hash FROM documents WHERE sha=?',(sha,)).fetchone()
        if not r or digest(r[0].encode())!=r[1]:raise SourceError('Published document integrity failed')
        manifest_path=self.document_publication(sha)
        if not manifest_path.exists():raise SourceError('Published document manifest is missing')
        manifest=json.loads(manifest_path.read_text())
        if manifest['document']!=r[1]:raise SourceError('Document publication manifest mismatch')
        return json.loads(r[0])
    def stored_passages(self,family=None,scope=None,region=None):
        clause=[];args=[]
        for column,value in (('family',family),('scope',scope),('region',region)):
            if value is not None:clause.append(column+'=?');args.append(value)
        sql='SELECT payload,payload_hash,embedding,embedding_hash,model_revision,document_sha FROM passages'
        if clause:sql+=' WHERE '+' AND '.join(clause)
        sql+=' ORDER BY document_sha,id'
        with self.connection() as db:rows=db.execute(sql,args).fetchall()
        out=[]
        for payload,phash,encoded,ehash,revision,sha in rows:
            if digest(payload.encode())!=phash or digest(encoded.encode())!=ehash or revision!=REVISION:raise SourceError('Stored passage integrity failed')
            vector=json.loads(encoded)
            if not vector or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in vector):raise SourceError('Invalid stored passage embedding')
            out.append((json.loads(payload),vector,sha))
        return out
    def document_families(self):
        with self.connection() as db:rows=db.execute('SELECT family,scope,region,count(*) FROM passages GROUP BY family,scope,region ORDER BY family').fetchall()
        families={}
        for family,scope,region,count in rows:
            families[family]={'scope':scope,'region':region,'passages':count,'head':self.document_head(family,region)}
        return families
    def search_passages(self,query,family=None,scope=None,region=None,limit=8,encoder=embed):
        """Whole-document retrieval over indexed passages; scores are ranks, never confidence."""
        if not isinstance(query,str) or not query.strip():raise SourceError('A retrieval query is required')
        stored=self.stored_passages(family=family,scope=scope,region=region)
        if not stored:return [],{'mode':'whole_document','candidates':0,'scores_are_confidence':False}
        terms=set(re.findall(r'[a-z0-9]+',norm(query)));qvector=encoder([query],query=True)[0]
        tokens=[re.findall(r'[a-z0-9]+',norm(p['text']+' '+(p.get('section') or ''))) for p,_,_ in stored]
        avg=sum(map(len,tokens))/len(tokens)
        lex=[];dense=[]
        for i,((passage,vector,sha),words) in enumerate(zip(stored,tokens)):
            if len(vector)!=len(qvector):raise SourceError('Embedding dimension mismatch')
            score=0.
            for term in terms:
                tf=words.count(term);df=sum(term in w for w in tokens);idf=math.log(1+(len(tokens)-df+.5)/(df+.5))
                score+=idf*tf*2.2/(tf+1.2*(.25+.75*len(words)/avg))
            lex.append((i,score));dense.append((i,sum(a*b for a,b in zip(qvector,vector))))
        lex.sort(key=lambda p:(-p[1],stored[p[0]][0]['id']));dense.sort(key=lambda p:(-p[1],stored[p[0]][0]['id']))
        ranks={i:0. for i in range(len(stored))}
        for ranked in [lex,dense]:
            for rank,(i,score) in enumerate(ranked,1):ranks[i]+=1/(60+rank)
        best=sorted(ranks,key=lambda i:(-ranks[i],stored[i][0]['id']))[:limit]
        results=[{**stored[i][0],'document_sha256':stored[i][2],'retrieval':{'rrf_score':ranks[i],'lexical_score':dict(lex)[i],'semantic_score':dict(dense)[i]}} for i in best]
        return results,{'mode':'whole_document_bm25_plus_dense_rrf','candidates':len(stored),'model':MODEL,'revision':REVISION,'filters':{'family':family,'scope':scope,'region':region},'scores_are_confidence':False}

