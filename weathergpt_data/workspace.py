"""Loopback-only forecast workspace. Database reads and explicit bounded refreshes."""
import argparse
import hmac
import json
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .answers import AnswerService, ROOT
from .ingestion import IngestionDB, run_one
from .rag import context_from_answer
from .documents import DocumentPruned
from .transport import SourceError, parsed, utcnow

DEFAULT_DATABASE=ROOT/'data/runtime/ingestion/ingestion.sqlite'
DEFAULT_RAW=ROOT/'data/runtime/ingestion/raw'
DEFAULT_GEOGRAPHY=ROOT/'data/processed/geography/source-inventory-20260912-v1/geography.sqlite'
# Document bodies are pruned after this many days; extracted passages and hashes are kept.
RETENTION_DAYS=7



class Workspace:
    def __init__(self, database=DEFAULT_DATABASE, raw_root=DEFAULT_RAW, geography=DEFAULT_GEOGRAPHY, clock=utcnow, opener=None):
        self.service=AnswerService(database,raw_root,geography,clock=clock)
        self.clock=clock;self.opener=opener
        self.conversation=None
        self._foundation=None

    def chat(self,body):
        from .conversation import ConversationEngine
        if self.conversation is None:self.conversation=ConversationEngine(self)
        return self.conversation.ask(body)

    DOCUMENT_STORE=ROOT/'data/runtime/documents'

    def document_index(self):
        from .bulletin_index import BulletinIndex,EXTRACTION_VERSION
        return BulletinIndex(self.service.raw_root.parent/'bulletins'/EXTRACTION_VERSION/'index.sqlite')

    def bulletin_pdf(self,sha):
        """Serve a verified source document body from whichever corpus published it.

        Bodies are pruned after the retention window while hashes and extracted text are
        kept, so a document that is published but whose body has gone raises DocumentPruned
        and is answered with 410. An identity that was never published is a plain not-found:
        the two must not be confused, because one says 'ask again differently' and the other
        says 'this never existed here'.
        """
        from .documents import DocumentPruned
        from .transport import digest,SourceError
        if not re.fullmatch(r'[a-f0-9]{64}',sha):raise SourceError('Invalid document identity')
        index=self.document_index()
        pruned=DocumentPruned(sha,'The source document body is outside the local retention window.')
        if (index.path.parent/'publications'/(sha+'.json')).exists():
            document=index.document_body_of_chunk_publication(sha)
            if document is None:raise pruned
            body=document
        elif index.document_publications(sha):
            published=index.passage_document(sha)
            blob=(published.get('provenance') or {}).get('blob') or published.get('blob')
            if not blob:raise SourceError('Published document records no body location')
            path=(self.DOCUMENT_STORE/blob).resolve()
            if self.DOCUMENT_STORE.resolve() not in path.parents:raise SourceError('Document body path leaves its store')
            if not path.exists():raise pruned
            body=path.read_bytes()
        else:
            raise SourceError('No published document carries this identity')
        if digest(body)!=sha:raise SourceError('Document changed during read')
        return body

    def document_retention(self,sha):
        """What is still held for a document whose body has been pruned."""
        index=self.document_index()
        published=index.passage_document(sha)
        with index.connection() as db:
            pages=[r[0] for r in db.execute('SELECT DISTINCT physical_page FROM (SELECT json_extract(payload,\'$.physical_page\') AS physical_page FROM passages WHERE document_sha=?) ORDER BY physical_page',(sha,))]
            passages=db.execute('SELECT count(*) FROM passages WHERE document_sha=?',(sha,)).fetchone()[0]
        return {'sha256':sha,'family':published.get('family'),'region':published.get('region'),
                'issue_date':published.get('issue_date'),'pages':published.get('pages'),
                'retained_passages':passages,'retained_physical_pages':pages,
                'extraction_version':published.get('extraction_version')}

    def arguments(self, body):
        if not isinstance(body,dict) or set(body)-{'question','entity_id','coordinates'}:
            raise ValueError('Use question and optional entity_id or coordinates')
        question=body.get('question')
        if not isinstance(question,str) or not 1<=len(question)<=500:raise ValueError('Enter a question of 1–500 characters')
        selection={k:body[k] for k in ('entity_id','coordinates') if k in body}
        if 'entity_id' in selection and (not isinstance(selection['entity_id'],str) or len(selection['entity_id'])!=64):
            raise ValueError('Select a valid place candidate')
        if 'coordinates' in selection:
            c=selection['coordinates']
            if not isinstance(c,dict) or set(c)!={'latitude','longitude'}:raise ValueError('Both latitude and longitude are required')
        return question,selection

    def answer(self, body):
        question,selection=self.arguments(body)
        answer=self.service.answer(question,**selection)
        return {'answer':answer,'context':context_from_answer(answer)}

    def refresh(self, body):
        packet=self.answer(body);answer=packet['answer']
        # Resolve the same user request first. Never substitute a guessed centroid.
        if not answer['request'] or (answer.get('location') or {}).get('status')!='selected_point':
            raise ValueError('Choose a place point or enter explicit coordinates before refreshing')
        now=self.clock();request=answer['request']
        if parsed(request['start_utc'])<=now:raise ValueError('Choose a future forecast interval')
        days=max(3,(parsed(request['end_utc']).date()-now.date()).days+1)
        if days>7:raise ValueError('Choose an interval within the next seven UTC calendar days')
        policy=json.loads(self.service.policy_path.read_text())
        source=policy.get('sources',{}).get('S21',{})
        registry=json.loads(self.service.registry_path.read_text())
        entry=next((p for p in registry['products'] if p['id']=='S21'),{})
        if (policy.get('schema_version')!='answer-policy-v1' or source.get('enabled') is not True
                or source.get('publication_policy')!='prototype_model_point_reference'
                or entry.get('integration',{}).get('status')!='prototype_adapter_tested'):
            raise ValueError('Forecast collection is disabled by the source policy')
        if packet['context']['status']=='eligible_prototype':
            packet['refresh']={'state':'already_fresh','provider_attempts':0,
                               'message':'The stored forecast is still within its serving lifetime.'}
            return packet
        p=answer['location']['requested_point']
        db=IngestionDB(self.service.ingestion_database,clock=self.clock)
        try:
            # One collection identity per point/horizon/hour; repeated clicks do not
            # bypass retry timing, exhausted jobs, provider cooldowns or budgets.
            cycle=now.replace(minute=0,second=0,microsecond=0).isoformat()
            jid=db.enqueue('forecast',p['latitude'],p['longitude'],days,cycle)
            before=db.db.execute('SELECT attempts FROM jobs WHERE id=?',(jid,)).fetchone()[0]
            worker=run_one(db,self.service.raw_root,self.opener,job_id=jid)
            job=dict(db.db.execute('SELECT state,attempts,due FROM jobs WHERE id=?',(jid,)).fetchone())
            # This measures claims; network reservations are independently recorded
            # by the governed opener. They are counted by job in the event ledger.
            attempts=db.db.execute("SELECT count(*) FROM events WHERE job_id=? AND kind='request_reserved'",(jid,)).fetchone()[0]
        finally:db.close()
        packet=self.answer(body)
        packet['refresh']={'state':job['state'],'job_id':jid,'worker_state':worker['state'],
                           'claims_this_action':max(0,job['attempts']-before),
                           'job_provider_attempts':attempts,'retry_due_utc_epoch':job['due'],
                           'message':('Collection completed; answer checked against the stored evidence.' if job['state']=='succeeded' else
                                      'Collection is '+job['state']+'. Retry timing and request limits remain in force; no background worker is running.')}
        return packet

    # Local retention and health read models. They expose the store to its owner
    # on loopback only; question text is never written to a log. Counts and job
    # states here are not forecast skill, coverage or operational readiness.
    def conversation_store(self):
        return self.service.ingestion_database.parent/'conversations.sqlite'

    # Product read-model surface. The Foundation shares the runtime store the rest of
    # the workspace already uses, so a cached official response is reused rather than
    # fetched again for a second view.
    def foundation(self):
        if self._foundation is None:
            from .foundation import Foundation
            from .transport import Store
            self._foundation=Foundation(Store(self.service.raw_root.parent.parent))
        return self._foundation

    def is_product(self,path):
        from . import product_api
        return path in product_api.PRODUCT_PATHS

    def product(self,path,params):
        from . import product_api
        if path not in product_api.PRODUCT_PATHS:return None
        return product_api.dispatch(self.foundation(),path,params)

    def map_layer(self,name):
        from . import product_api
        return product_api.map_layer_path(name).read_bytes()

    def conversations(self,limit=40):
        path=self.conversation_store()
        limit=max(1,min(int(limit),200))
        if not path.exists():
            return {'schema_version':'conversation-ledger-v1','total':0,'limit':limit,'conversations':[],
                    'note':'No local conversation store exists yet; the first question creates it.'}
        db=sqlite3.connect(path)
        try:
            rows=db.execute('SELECT id,payload,updated FROM conversations ORDER BY updated DESC LIMIT ?',(limit,)).fetchall()
            total=db.execute('SELECT count(*) FROM conversations').fetchone()[0]
        finally:db.close()
        items=[]
        for cid,payload,updated in rows:
            try:state=json.loads(payload) if payload else {}
            except ValueError:state={}
            history=state.get('history') or []
            opening=next((turn.get('content') for turn in history if turn.get('role')=='user'),'')
            items.append({'id':cid,'updated':updated,'turns':len(history),
                          'asked':sum(1 for turn in history if turn.get('role')=='user'),
                          'opening_question':excerpt(opening)})
        return {'schema_version':'conversation-ledger-v1','total':total,'limit':limit,'conversations':items,
                'note':'Stored on this machine for the person who asked. Excerpts are served over loopback only and never written to logs.'}

    def conversation_transcript(self,cid):
        _conversation_id(cid)
        path=self.conversation_store()
        if not path.exists():raise SourceError('This conversation is not in the local store. Start a new conversation.')
        db=sqlite3.connect(path)
        try:row=db.execute('SELECT payload,updated FROM conversations WHERE id=?',(cid,)).fetchone()
        finally:db.close()
        if row is None:raise SourceError('This conversation is not in the local store. Start a new conversation.')
        try:state=json.loads(row[0]) if row[0] else {}
        except ValueError:state={}
        turns=[{'role':turn.get('role'),'content':turn.get('content')} for turn in (state.get('history') or []) if turn.get('content')]
        return {'schema_version':'conversation-transcript-v1','id':cid,'updated':row[1],'turns':turns,
                'note':'Restored transcript. Earlier answers are timestamped receipts from the moment they were retrieved; ask again before relying on one.'}

    def delete_conversation(self,cid):
        _conversation_id(cid)
        path=self.conversation_store()
        if not path.exists():raise SourceError('This conversation is not in the local store.')
        with sqlite3.connect(path) as db:removed=db.execute('DELETE FROM conversations WHERE id=?',(cid,)).rowcount
        return {'schema_version':'conversation-delete-v1','id':cid,'deleted':max(0,removed),
                'note':'Removed from the local conversation store. Saved source documents and published evidence are unaffected.'}

    def health(self):
        # Streams are pseudonymous point identities, so this reports what was
        # collected and when, never which coordinates made up a stream.
        database=self.service.ingestion_database
        if not database.exists():
            return {'schema_version':'source-health-v1','available':False,'products':[],'job_states':{},'active_leases':0,'cooldowns':[],'total_jobs':0,'streams':0,
                    'note':'No ingestion store exists yet, so there is no collection history to report.'}
        now=time.time()
        db=sqlite3.connect(database)
        try:
            specs=db.execute('SELECT id,spec,state FROM jobs').fetchall()
            commits=dict((job_id,committed) for job_id,committed in db.execute('SELECT job_id,committed FROM versions'))
            job_states=dict(db.execute('SELECT state,count(*) FROM jobs GROUP BY state').fetchall())
            streams=db.execute('SELECT count(DISTINCT stream) FROM jobs').fetchone()[0]
            leases=db.execute('SELECT count(*) FROM requests WHERE finished=0 AND lease_until>?',(now,)).fetchone()[0]
            cooldowns=db.execute('SELECT provider,until FROM cooldowns WHERE until>? ORDER BY until',(now,)).fetchall()
        finally:db.close()
        products={}
        for job_id,spec,state in specs:
            try:product=(json.loads(spec) or {}).get('product') or 'unlabelled'
            except (TypeError,ValueError):product='unlabelled'
            entry=products.setdefault(product,{'product':product,'jobs':0,'states':{},'newest_commit_utc':None})
            entry['jobs']+=1;entry['states'][state]=entry['states'].get(state,0)+1
            committed=commits.get(job_id)
            if committed is not None:
                stamp_value=stamp(committed)
                if entry['newest_commit_utc'] is None or committed>entry['newest_commit_utc_value']:
                    entry['newest_commit_utc']=stamp_value;entry['newest_commit_utc_value']=committed
        for entry in products.values():entry.pop('newest_commit_utc_value',None)
        return {'schema_version':'source-health-v1','available':True,
                'products':sorted(products.values(),key=lambda entry:entry['product']),
                'job_states':job_states,'total_jobs':len(specs),'streams':streams,'active_leases':leases,
                'cooldowns':[{'provider':provider,'until_utc':stamp(until)} for provider,until in cooldowns],
                'note':'Read-only projection of the local ingestion store: which products were collected, what happened to those jobs, and when the newest evidence was committed. A stream is a pseudonymous point identity, so no requested location is shown here. These counts are not coverage, forecast skill or operational readiness.'}


def excerpt(text,limit=96):
    text=' '.join(str(text or '').split())
    return text if len(text)<=limit else text[:limit-1].rstrip()+'\u2026'


def stamp(value):
    if value is None:return None
    return datetime.fromtimestamp(float(value),timezone.utc).isoformat()


def _conversation_id(cid):
    import uuid
    try:uuid.UUID(cid)
    except (ValueError,TypeError,AttributeError):raise SourceError('Invalid conversation identifier')


def make_server(workspace, port=8765):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass  # Do not log private questions or coordinates.

        def respond(self, code, data, kind='application/json'):
            if kind=='application/json':data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
            elif isinstance(data,str):data=data.encode()
            self.send_response(code)
            self.send_header('Content-Type',kind+'; charset=utf-8')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers();self.wfile.write(data)

        def allowed_host(self):
            return self.headers.get('Host')=='127.0.0.1:'+str(self.server.server_port)

        def authorized(self):
            return hmac.compare_digest(self.headers.get('X-WeatherGPT-Token',''),token)

        def do_GET(self):
            if not self.allowed_host():return self.respond(403,{'error':'Use the loopback URL printed by the server'})
            path=urlsplit(self.path).path
            if path.startswith('/api/documents/'):
                sha=path.removeprefix('/api/documents/')
                try:return self.respond(200,workspace.bulletin_pdf(sha),'application/pdf')
                except DocumentPruned as pruned:
                    # The document is known and its passages are still indexed; only the
                    # body is outside the retention window. Say that rather than 404.
                    payload={'error':pruned.detail,
                             'retention_days':RETENTION_DAYS,
                             'retained':'the document hash and its extracted pages remain indexed and citable',
                             'sha256':pruned.sha}
                    try:payload['document']=workspace.document_retention(pruned.sha)
                    except (ValueError,OSError,KeyError,sqlite3.Error,SourceError):pass
                    return self.respond(410,payload)
                except (ValueError,OSError,KeyError,sqlite3.Error):return self.respond(404,{'error':'Verified source document is unavailable'})
            # Stored conversations and collection health are the owner's data, so they
            # require the session token as well as the loopback Host check. Any other
            # API path keeps the existing 404 behaviour.
            if path.startswith('/api/'):
                known=(workspace.is_product(path) or path=='/api/conversations' or path=='/api/health'
                       or path.startswith('/api/conversations/') or path.startswith('/api/map/static/'))
                if not known:return self.respond(404,{'error':'Not found'})
                if not self.authorized():return self.respond(403,{'error':'Reload this local workspace before reading stored data'})
                try:
                    if path=='/api/conversations':return self.respond(200,workspace.conversations())
                    if path=='/api/health':return self.respond(200,workspace.health())
                    if path.startswith('/api/conversations/'):return self.respond(200,workspace.conversation_transcript(path.removeprefix('/api/conversations/')))
                    if path.startswith('/api/map/static/'):
                        return self.respond(200,workspace.map_layer(path.removeprefix('/api/map/static/')),'application/geo+json')
                    view=workspace.product(path,parse_qs(urlsplit(self.path).query))
                    if view is None:return self.respond(404,{'error':'Not found'})
                    return self.respond(200,view)
                except ValueError as exc:return self.respond(400,{'error':str(exc)})
                except (OSError,sqlite3.Error):return self.respond(503,{'error':'The local evidence store is unavailable. Check its files and retry.'})
            assets={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/views.js':('views.js','text/javascript'),'/charts.js':('charts.js','text/javascript'),'/shell.js':('shell.js','text/javascript'),'/panels.js':('panels.js','text/javascript'),'/map.js':('map.js','text/javascript'),'/style.css':('style.css','text/css')}
            if path not in assets:return self.respond(404,{'error':'Not found'})
            filename,kind=assets[path]
            try:text=(ROOT/'web'/filename).read_text()
            except OSError:return self.respond(404,{'error':'This workspace file is missing; restart the workspace from a complete checkout.'})
            if filename=='index.html':text=text.replace('__WORKSPACE_TOKEN__',token)
            self.respond(200,text,kind)

        def do_DELETE(self):
            if not self.allowed_host() or not self.authorized():
                return self.respond(403,{'error':'Reload this local workspace before deleting a stored conversation'})
            path=urlsplit(self.path).path
            if not path.startswith('/api/conversations/'):return self.respond(404,{'error':'Not found'})
            try:return self.respond(200,workspace.delete_conversation(path.removeprefix('/api/conversations/')))
            except ValueError as exc:return self.respond(400,{'error':str(exc)})
            except (OSError,sqlite3.Error):return self.respond(503,{'error':'The local evidence store is unavailable. Check its files and retry.'})

        def do_POST(self):
            origin='http://127.0.0.1:'+str(self.server.server_port)
            supplied=self.headers.get('X-WeatherGPT-Token','')
            if (not self.allowed_host() or self.headers.get('Origin',origin)!=origin
                    or not hmac.compare_digest(supplied,token)):
                return self.respond(403,{'error':'Reload this local workspace before sending a request'})
            if self.path not in {'/api/answer','/api/refresh','/api/chat'}:return self.respond(404,{'error':'Not found'})
            try:
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('Send JSON')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=8192:raise ValueError('Request must be 1–8192 bytes')
                body=json.loads(self.rfile.read(length),parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Non-finite JSON')))
                result=workspace.chat(body) if self.path=='/api/chat' else workspace.refresh(body) if self.path=='/api/refresh' else workspace.answer(body)
                self.respond(200,result)
            except (ValueError,TypeError,KeyError) as exc:self.respond(400,{'error':str(exc)})
            except (OSError,sqlite3.Error):self.respond(503,{'error':'The local evidence store is unavailable. Check its files and retry.'})

    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--database',type=Path,default=DEFAULT_DATABASE)
    p.add_argument('--raw-root',type=Path,default=DEFAULT_RAW)
    p.add_argument('--geography-database',type=Path,default=DEFAULT_GEOGRAPHY)
    a=p.parse_args()
    server=make_server(Workspace(a.database,a.raw_root,a.geography_database),a.port)
    print('WeatherGPT: http://127.0.0.1:'+str(server.server_port)+' — local prototype; Ctrl-C to stop.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
