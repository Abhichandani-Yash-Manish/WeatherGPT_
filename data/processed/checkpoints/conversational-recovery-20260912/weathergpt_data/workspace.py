"""Loopback-only forecast workspace. Database reads and explicit bounded refreshes."""
import argparse
import hmac
import json
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .answers import AnswerService, ROOT
from .ingestion import IngestionDB, run_one
from .rag import context_from_answer
from .transport import parsed, utcnow

DEFAULT_DATABASE=ROOT/'data/runtime/ingestion/ingestion.sqlite'
DEFAULT_RAW=ROOT/'data/runtime/ingestion/raw'
DEFAULT_GEOGRAPHY=ROOT/'data/processed/geography/source-inventory-20260912-v1/geography.sqlite'


class Workspace:
    def __init__(self, database=DEFAULT_DATABASE, raw_root=DEFAULT_RAW, geography=DEFAULT_GEOGRAPHY, clock=utcnow, opener=None):
        self.service=AnswerService(database,raw_root,geography,clock=clock)
        self.clock=clock;self.opener=opener
        self.conversation=None

    def chat(self,body):
        from .conversation import ConversationEngine
        if self.conversation is None:self.conversation=ConversationEngine(self)
        return self.conversation.ask(body)

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

        def do_GET(self):
            if not self.allowed_host():return self.respond(403,{'error':'Use the loopback URL printed by the server'})
            path=urlsplit(self.path).path
            assets={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
            if path not in assets:return self.respond(404,{'error':'Not found'})
            filename,kind=assets[path]
            text=(ROOT/'web'/filename).read_text()
            if filename=='index.html':text=text.replace('__WORKSPACE_TOKEN__',token)
            self.respond(200,text,kind)

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
