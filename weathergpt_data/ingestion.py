"""Bounded, explicitly invoked local ingestion. SQLite leases fence late workers.

Collection cycle ordering is not publisher run ordering. All outputs remain
prototype numeric evidence with source freshness and geographic applicability open.
"""
import json
import math
import random
import sqlite3
import urllib.error
import urllib.request
import uuid
import fcntl
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse,parse_qs

from .geography import canonical, identity, point
from .transport import Store, SourceError, parsed, stamp, utcnow
from .foundation import Foundation
from .adapters import FORECAST,MARINE,EXTENDED,HISTORY_LOCAL,REANALYSIS_MODELS,temporal_support

PRODUCTS = {'forecast': ('S21', 'weather_forecast', 'api.open-meteo.com', '/v1/gfs', 4),
            'marine': ('S56', 'marine_forecast', 'marine-api.open-meteo.com', '/v1/marine', 3),
            'river': ('S37', 'river_discharge', 'flood-api.open-meteo.com', '/v1/flood', 1)}
PRODUCTS.update(extended_forecast=('S62','extended_weather_forecast','api.open-meteo.com','/v1/forecast',len(EXTENDED)),
                history_local=('S22','reanalysis','archive-api.open-meteo.com','/v1/archive',len(HISTORY_LOCAL)))
# Local prototype ceilings shared by all supported Open-Meteo endpoints. Not provider entitlements.
LIMITS = ((60, 20), (3600, 100), (86400, 200), (31*86400, 1000))


def request_parameters(spec):
    if spec['product']=='history_local':
        return {'latitude':str(spec['latitude']),'longitude':str(spec['longitude']),
                'start_date':spec['start_date'],'end_date':spec['end_date'],
                'daily':','.join(HISTORY_LOCAL),'models':spec.get('models','era5'),'timezone':'Asia/Kolkata'}
    params={'latitude':str(spec['latitude']),'longitude':str(spec['longitude']),'forecast_days':str(spec['days'])}
    if spec['product']=='river':params['daily']='river_discharge'
    else:
        params.update(hourly=','.join(FORECAST if spec['product']=='forecast' else EXTENDED if spec['product']=='extended_forecast' else MARINE),timezone='UTC',timeformat='unixtime')
        if spec['product'] in {'forecast','extended_forecast'}:params.update(temperature_unit='celsius',wind_speed_unit='kmh',precipitation_unit='mm')
        else:params['cell_selection']='sea'
    return params


def epoch(value):
    if isinstance(value, str): value = parsed(value)
    if value.tzinfo is None: raise ValueError('Timezone required')
    result = value.timestamp()
    if not math.isfinite(result): raise ValueError('Finite timestamp required')
    return result


def iso(value): return datetime.fromtimestamp(value,timezone.utc).isoformat()


def retry_after(value, now):
    """RFC delay-seconds or HTTP-date, never truncate a valid publisher wait."""
    if not value: return None
    try:
        text = str(value).strip()
        if text.isascii() and text.isdigit():
            delay = int(text)
            # Unrepresentable waits fail closed until explicit investigation.
            return min(epoch(now)+delay, 253402300799.0)
        date = parsedate_to_datetime(text)
        return max(epoch(now), epoch(date))
    except (ValueError, TypeError, OverflowError): return None


class IngestionDB:
    def __init__(self, path, clock=utcnow, readonly=False):
        self.path = Path(path).resolve()
        self.clock = clock
        if readonly:
            self.db = sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,timeout=10,isolation_level=None)
        else:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            self.db = sqlite3.connect(self.path,timeout=10,isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        if readonly:return
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, stream TEXT NOT NULL, cycle REAL NOT NULL,
                expires REAL NOT NULL, spec TEXT NOT NULL, state TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL,
                due REAL NOT NULL, token TEXT, lease_until REAL, last_error TEXT);
            CREATE INDEX IF NOT EXISTS jobs_due ON jobs(state,due);
            CREATE TABLE IF NOT EXISTS versions (
                job_id TEXT PRIMARY KEY REFERENCES jobs(id), stream TEXT NOT NULL,
                cycle REAL NOT NULL, committed REAL NOT NULL, sha256 TEXT NOT NULL,
                result TEXT NOT NULL, coverage TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS heads (
                stream TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES versions(job_id));
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, at REAL NOT NULL, job_id TEXT, kind TEXT NOT NULL, detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY, provider TEXT NOT NULL, at REAL NOT NULL,
                lease_until REAL NOT NULL, finished INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS request_budget ON requests(provider,at);
            CREATE TABLE IF NOT EXISTS cooldowns (provider TEXT PRIMARY KEY, until REAL NOT NULL);
        ''')

    def close(self): self.db.close()

    @contextmanager
    def read_snapshot(self):
        """All selection/health reads in one SQLite snapshot; no queue mutation."""
        nested=self.db.in_transaction
        if not nested:self.db.execute('BEGIN')
        try:
            yield
        finally:
            if not nested:self.db.execute('ROLLBACK')

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK'); raise

    def event(self, job, kind, detail):
        self.db.execute('INSERT INTO events(at,job_id,kind,detail) VALUES (?,?,?,?)',
                        (epoch(self.clock()),job,kind,canonical(detail)))

    def enqueue(self, product, latitude, longitude, days, cycle_at, max_attempts=4, *, start_date=None, end_date=None, models=None):
        if product not in PRODUCTS: raise ValueError('Unsupported governed numeric product')
        point(latitude,longitude)
        if type(days) is not int or not 1 <= days <= 7: raise ValueError('Worker supports 1–7 whole days')
        if type(max_attempts) is not int or not 1 <= max_attempts <= 6: raise ValueError('Use 1–6 attempts')
        cycle = epoch(cycle_at); dt = datetime.fromtimestamp(cycle,timezone.utc)
        end = dt.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)
        spec = {'contract':'numeric-ingestion-v1','product':product,'latitude':float(latitude),
                'longitude':float(longitude),'days':days,'request_date':dt.date().isoformat()}
        if product=='history_local':
            from datetime import date
            model=models or 'era5'
            a,b=date.fromisoformat(start_date),date.fromisoformat(end_date)
            if model not in REANALYSIS_MODELS:raise ValueError('Unsupported reanalysis model: '+str(model))
            if (b-a).days+1!=days or a.year<1940 or b>=dt.date():raise ValueError('Invalid historical dates or daily horizon')
            # The model is part of the request identity: a different reanalysis model is a
            # different collection, never a cache hit on another model's payload.
            spec.update(start_date=start_date,end_date=end_date,models=model)
        elif start_date is not None or end_date is not None:raise ValueError('Explicit dates only belong to daily history')
        stream = identity({k:v for k,v in spec.items() if k!='request_date'})
        jid = identity([stream,stamp(dt),spec])
        with self.transaction():
            old = self.db.execute('SELECT max_attempts FROM jobs WHERE id=?',(jid,)).fetchone()
            if old:
                if old[0]!=max_attempts: raise ValueError('Existing job policy is immutable')
                return jid
            active = self.db.execute("SELECT count(*) FROM jobs WHERE state IN ('pending','retry','running')").fetchone()[0]
            if active >= 1000: raise ValueError('Local queue capacity is 1000 unfinished jobs')
            self.db.execute('INSERT INTO jobs(id,stream,cycle,expires,spec,state,max_attempts,due) VALUES (?,?,?,?,?,?,?,?)',
                            (jid,stream,cycle,end.timestamp(),canonical(spec),'pending',max_attempts,cycle))
            self.event(jid,'enqueued',spec)
        return jid

    def claim(self, lease_seconds=120, job_id=None):
        if type(lease_seconds) is not int or not 30 <= lease_seconds <= 600: raise ValueError('Lease must be 30–600 seconds')
        now = epoch(self.clock())
        with self.transaction():
            rows = self.db.execute("SELECT * FROM jobs WHERE state IN ('pending','retry','running') AND (expires<=? OR (state='running' AND lease_until<=?))",(now,now)).fetchall()
            for row in rows:
                state = 'expired' if row['expires']<=now else ('failed' if row['attempts']>=row['max_attempts'] else 'retry')
                self.db.execute('UPDATE jobs SET state=?,token=NULL,lease_until=NULL,due=? WHERE id=?',(state,now,row['id']))
                self.event(row['id'],'lease_recovery',{'state':state})
            target_clause=' AND id=?' if job_id is not None else ''
            args=(now,now,job_id) if job_id is not None else (now,now)
            row = self.db.execute("SELECT * FROM jobs WHERE state IN ('pending','retry') AND due<=? AND expires>?"+target_clause+" ORDER BY due,id LIMIT 1",args).fetchone()
            if row is None: return None
            token = uuid.uuid4().hex
            self.db.execute("UPDATE jobs SET state='running',attempts=attempts+1,token=?,lease_until=? WHERE id=?",(token,now+lease_seconds,row['id']))
            self.event(row['id'],'claimed',{'token':token})
            return dict(self.db.execute('SELECT * FROM jobs WHERE id=?',(row['id'],)).fetchone())

    def owned(self, job):
        row = self.db.execute('SELECT * FROM jobs WHERE id=?',(job['id'],)).fetchone()
        if row is None or row['state']!='running' or row['token']!=job['token'] or row['lease_until']<=epoch(self.clock()):
            raise ValueError('Worker lease lost; late worker cannot publish or reschedule')
        return row

    def fail(self, job, error, jitter=None):
        now = epoch(self.clock()); jitter = random.random() if jitter is None else jitter
        if not 0 <= jitter <= 1: raise ValueError('Jitter must be between zero and one')
        with self.transaction():
            row = self.owned(job)
            deferred = bool(getattr(error,'deferred',False)); retryable = bool(getattr(error,'retryable',False))
            attempts = row['attempts']-int(deferred)
            delay = min(900, 5*2**max(0,attempts-1))*(1+jitter)
            due = max(now+delay,getattr(error,'retry_at',None) or 0)
            state = 'expired' if now>=row['expires'] or due>=row['expires'] else (
                'retry' if (deferred or retryable) and attempts<row['max_attempts'] else 'failed')
            detail = {'message':str(error),'retryable':retryable,'deferred':deferred,
                      'http_status':getattr(error,'http_status',None),'next_attempt_at':iso(due)}
            self.db.execute('UPDATE jobs SET state=?,attempts=?,due=?,last_error=?,token=NULL,lease_until=NULL WHERE id=?',
                            (state,attempts,due,canonical(detail),job['id']))
            self.event(job['id'],state,detail)
            return state

    def complete(self, job, result):
        spec = json.loads(job['spec']); sid,family,_,_,variables = PRODUCTS[spec['product']]
        meta = result.get('provenance',{}); quality = result.get('quality',{})
        attempt=meta.get('ingestion_attempt',{})
        if attempt.get('job_id')!=job['id'] or attempt.get('token')!=job['token']:
            raise ValueError('Result belongs to another job attempt')
        if result.get('source_id')!=sid or result.get('family')!=family or meta.get('validation_scope')!='product' or meta.get('delivery')!='network':
            raise ValueError('Only freshly fetched, product-validated matching data can complete a job')
        if quality.get('schema')!='validated' or quality.get('interval_coverage')!='complete' or quality.get('value_coverage')!='complete':
            raise ValueError('Incomplete or missing numeric coverage cannot replace the current version')
        daily=spec['product'] in {'river','history_local'}
        expected = spec['days']*variables*(1 if daily else 24)
        if result.get('count')!=expected or len(result.get('records',[]))!=expected: raise ValueError('Record count does not satisfy job')
        requested = result.get('coverage',{}).get('requested_point')
        if requested!={'latitude':spec['latitude'],'longitude':spec['longitude']}: raise ValueError('Result belongs to another requested location')
        start = parsed(spec['start_date']+'T00:00:00+05:30') if spec['product']=='history_local' else parsed(spec['request_date']+'T00:00:00Z')
        end = start+timedelta(days=spec['days'])
        times = [r.get('period_start_utc') if daily else r.get('valid_time_utc') for r in result['records']]
        expected_times = {stamp(start+timedelta(days=i)) for i in range(spec['days'])} if daily else {stamp(start+timedelta(hours=i)) for i in range(spec['days']*24)}
        if {stamp(parsed(t)) for t in times} != expected_times: raise ValueError('Result interval differs from fixed job date')
        support=temporal_support(result['records'])
        parameters=set({'forecast':FORECAST,'extended_forecast':EXTENDED,'history_local':HISTORY_LOCAL,'marine':MARINE,'river':{'river_discharge'}}[spec['product']])
        if set(support)!=parameters or any(v['sample_count']!=expected//variables for v in support.values()):
            raise ValueError('Every required variable must cover the complete sample axis')
        encoded = canonical(result)
        receipt = {'schema_version':'numeric-coverage-v2','product':family,'source_id':sid,'requested_point':requested,
                   'returned_point':result['coverage']['returned_grid'],'window_start':stamp(start),'window_end':stamp(end),
                   'window_semantics':'sample_timestamp_window; use variables for accumulation intervals','variables':support,
                   'expected':expected,'validated':expected,'missing':0,'quarantined':0,
                   'source_sha256':meta['sha256'],'source_issue_freshness':'unknown',
                   'spatial_applicability':'unresolved','operational_eligible':False,
                   'scope':'Numeric schema/window evidence; timestamps are samples, not a district area average or warning.'}
        now = epoch(self.clock())
        with self.transaction():
            row = self.owned(job)
            if now >= row['expires']: raise ValueError('Job request date expired during fetch')
            self.db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?,?)',
                            (row['id'],row['stream'],row['cycle'],now,identity(result),encoded,canonical(receipt)))
            head = self.db.execute('SELECT v.cycle FROM heads h JOIN versions v ON v.job_id=h.job_id WHERE h.stream=?',(row['stream'],)).fetchone()
            promoted = head is None or row['cycle']>head[0]
            if promoted:
                self.db.execute('INSERT INTO heads VALUES (?,?) ON CONFLICT(stream) DO UPDATE SET job_id=excluded.job_id',(row['stream'],row['id']))
            self.db.execute("UPDATE jobs SET state='succeeded',token=NULL,lease_until=NULL WHERE id=?",(row['id'],))
            self.event(row['id'],'completed',{'promoted':promoted,'source_sha256':meta['sha256']})
        return {'state':'succeeded','promoted':promoted,'job_id':row['id']}

    def reserve(self, provider='open-meteo', limits=LIMITS, lease_seconds=60):
        if not limits or any(type(w) is not int or type(n) is not int or w<=0 or n<=0 for w,n in limits):
            raise ValueError('Budget windows and limits must be positive whole numbers')
        now = epoch(self.clock())
        with self.transaction():
            pause = self.db.execute('SELECT until FROM cooldowns WHERE provider=?',(provider,)).fetchone()
            waits = [pause[0]] if pause and pause[0]>now else []
            running = self.db.execute('SELECT max(lease_until) FROM requests WHERE provider=? AND finished=0 AND lease_until>?',(provider,now)).fetchone()[0]
            if running: waits.append(running)
            for window,limit in limits:
                rows = self.db.execute('SELECT at FROM requests WHERE provider=? AND at>? ORDER BY at',(provider,now-window)).fetchall()
                if len(rows)>=limit: waits.append(rows[len(rows)-limit][0]+window)
            if waits: raise SourceError('Provider budget, cooldown or concurrency slot unavailable',retryable=True,deferred=True,retry_at=max(waits))
            rid = uuid.uuid4().hex
            self.db.execute('INSERT INTO requests(id,provider,at,lease_until) VALUES (?,?,?,?)',(rid,provider,now,now+lease_seconds))
        return rid

    def release(self, request_id, cooldown=None):
        with self.transaction():
            row = self.db.execute('SELECT provider FROM requests WHERE id=?',(request_id,)).fetchone()
            if row is None: raise ValueError('Unknown request reservation')
            self.db.execute('UPDATE requests SET finished=1 WHERE id=?',(request_id,))
            if cooldown:
                self.db.execute('INSERT INTO cooldowns VALUES (?,?) ON CONFLICT(provider) DO UPDATE SET until=max(until,excluded.until)',(row[0],cooldown))

    def status(self):
        return {'jobs':dict(self.db.execute('SELECT state,count(*) FROM jobs GROUP BY state')),
                'versions':self.db.execute('SELECT count(*) FROM versions').fetchone()[0],
                'heads':self.db.execute('SELECT count(*) FROM heads').fetchone()[0],
                'network_attempts_reserved':self.db.execute('SELECT count(*) FROM requests').fetchone()[0],
                'operational_ready':False}

    def latest(self, stream):
        with self.read_snapshot():return self._latest(stream)

    def _latest(self, stream):
        now=epoch(self.clock())
        def job_summary(row):
            if row is None:return None
            item=dict(row);item['last_error']=json.loads(item['last_error']) if item['last_error'] else None
            return item
        columns='id,state,cycle,expires,due,lease_until,last_error'
        latest=job_summary(self.db.execute('SELECT '+columns+' FROM jobs WHERE stream=? AND cycle<=? ORDER BY cycle DESC LIMIT 1',(stream,now)).fetchone())
        future=job_summary(self.db.execute('SELECT '+columns+' FROM jobs WHERE stream=? AND cycle>? ORDER BY cycle LIMIT 1',(stream,now)).fetchone())
        health='no_due_collection'
        if latest:
            health=latest['state']
            if latest['state'] in {'pending','retry','running'} and latest['expires']<=now:health='expired'
            elif latest['state']=='running' and (latest['lease_until'] is None or latest['lease_until']<=now):health='lease_expired'
            elif latest['state']=='pending' and latest['due']<now:health='overdue_pending'
        scheduling={'latest_collection_job':latest,'next_planned_collection':future,'refresh_health':health}
        row = self.db.execute('SELECT v.*,j.expires FROM heads h JOIN versions v ON v.job_id=h.job_id JOIN jobs j ON j.id=v.job_id WHERE h.stream=?',(stream,)).fetchone()
        if row is None: return {'status':'unavailable','operational_eligible':False,**scheduling}
        result = json.loads(row['result'])
        if identity(result)!=row['sha256']: raise ValueError('Published payload hash mismatch')
        state='prototype_snapshot'
        if latest and latest['cycle']>row['cycle'] and health in {'retry','failed','expired','overdue_pending','lease_expired'}:state='refresh_failed_or_missed'
        elif latest and latest['cycle']>row['cycle']:state='refresh_pending'
        if now>=row['expires']:state='request_date_expired'
        if row['committed']>now or row['cycle']>now:state='not_available_at_requested_time'
        return {'status':state,**scheduling,
                'job_id':row['job_id'],'collection_cycle_at':iso(row['cycle']),
                'committed_at':iso(row['committed']),'retrieval_age_seconds':epoch(self.clock())-epoch(result['provenance']['retrieved_at_utc']),
                'result':result,'coverage':json.loads(row['coverage']),'operational_eligible':False}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None


class GovernedOpener:
    def __init__(self, database, job, opener=None):
        self.database=database; self.job=job
        self.opener=opener or urllib.request.build_opener(NoRedirect()).open

    @contextmanager
    def __call__(self, request, timeout=25):
        spec=json.loads(self.job['spec']); _,_,host,path,_=PRODUCTS[spec['product']]
        url=urlparse(request.full_url)
        if url.scheme!='https' or url.netloc!=host or url.path!=path or request.get_method()!='GET':
            raise SourceError('Request outside the reviewed single-product endpoint contract')
        actual=parse_qs(url.query,keep_blank_values=True)
        if actual!={k:[v] for k,v in request_parameters(spec).items()}:
            raise SourceError('Request variables, location or horizon exceed the budgeted job contract')
        self.database.owned(self.job)
        lock=self.database.path.with_suffix('.open-meteo-network.lock').open('a')
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            raise SourceError('Provider request already in progress',retryable=True,deferred=True,retry_at=epoch(self.database.clock())+5)
        try:
            rid=self.database.reserve()
        except BaseException:
            lock.close(); raise
        cooldown=None
        try:
            self.database.event(self.job['id'],'request_reserved',{'reservation_id':rid})
            with self.opener(request,timeout=timeout) as response:
                if response.status!=200:
                    raise urllib.error.HTTPError(request.full_url,response.status,'Unexpected HTTP response',response.headers,None)
                yield response
        except urllib.error.HTTPError as exc:
            retryable=exc.code in {408,429} or 500<=exc.code<=599
            if retryable:
                cooldown=retry_after(exc.headers.get('Retry-After') if exc.headers else None,self.database.clock())
                cooldown=max(cooldown or 0,epoch(self.database.clock())+(60 if exc.code==429 else 5))
            raise SourceError('HTTP '+str(exc.code),retryable=retryable,retry_at=cooldown,http_status=exc.code) from exc
        except (urllib.error.URLError,TimeoutError,ConnectionError) as exc:
            raise SourceError(str(exc),retryable=True) from exc
        finally:
            try:self.database.release(rid,cooldown)
            finally:lock.close()


def run_one(database, raw_root, opener=None, job_id=None):
    job=database.claim(job_id=job_id)
    if job is None: return {'state':'idle'}
    spec=json.loads(job['spec'])
    # Attempt-specific cache pointers cannot be overwritten by a worker with an obsolete lease.
    store=Store(Path(raw_root)/job['id']/job['token'],clock=database.clock,
                opener=GovernedOpener(database,job,opener))
    try:
        if spec['product']!='history_local' and database.clock().astimezone(timezone.utc).date().isoformat()!=spec['request_date']:
            raise SourceError('Fixed request date no longer matches the provider relative-date API')
        if spec['product']=='history_local':
            result=Foundation(store).history_local(spec['latitude'],spec['longitude'],spec['start_date'],spec['end_date'],refresh=True,models=spec.get('models','era5'))
        else:result=getattr(Foundation(store),spec['product'])(spec['latitude'],spec['longitude'],spec['days'],refresh=True)
        result['provenance']['ingestion_attempt']={'job_id':job['id'],'token':job['token'],
                                                  'relative_root':job['id']+'/'+job['token']}
        return database.complete(job,result)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        try: state=database.fail(job,exc)
        except ValueError: return {'state':'lease_lost','job_id':job['id']}
        return {'state':state,'job_id':job['id'],'error':str(exc)}


def run_batch(database, raw_root, max_jobs=10, opener=None):
    if type(max_jobs) is not int or not 1<=max_jobs<=100: raise ValueError('Run 1–100 jobs per invocation')
    results=[]
    for _ in range(max_jobs):
        result=run_one(database,raw_root,opener)
        if result['state']=='idle': break
        results.append(result)
    return {'results':results,'status':database.status(),'scheduled_background_work':False}


def safe_member(value):
    if not isinstance(value,str) or not value:raise ValueError('Missing backup member path')
    path=Path(value)
    if path.is_absolute() or '..' in path.parts or str(path)!=value:raise ValueError('Unsafe backup member')
    return path


def validate_backup_content(directory, members):
    """Check completeness as well as physical integrity, including legacy bundles."""
    from contextlib import closing
    import hashlib
    directory=Path(directory)
    if not isinstance(members,dict) or 'ingestion.sqlite' not in members:
        raise ValueError('Backup must include ingestion.sqlite')
    required={
        'jobs':{'id','stream','cycle','expires','spec','state','attempts','max_attempts','due','token','lease_until','last_error'},
        'versions':{'job_id','stream','cycle','committed','sha256','result','coverage'},
        'heads':{'stream','job_id'},'events':{'id','at','job_id','kind','detail'},
        'requests':{'id','provider','at','lease_until','finished'},'cooldowns':{'provider','until'},
    }
    with closing(sqlite3.connect((directory/'ingestion.sqlite').resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        for table,columns in required.items():
            if not columns <= {r['name'] for r in db.execute('PRAGMA table_info('+table+')')}:
                raise ValueError('Missing backup schema: '+table)
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Backup database integrity failed')
        for row in db.execute('SELECT * FROM versions'):
            job=db.execute('SELECT * FROM jobs WHERE id=?',(row['job_id'],)).fetchone()
            if job is None or job['state']!='succeeded' or (job['stream'],job['cycle'])!=(row['stream'],row['cycle']):
                raise ValueError('Backup version does not match a successful job')
            result=json.loads(row['result']);meta=result['provenance']
            receipt=json.loads(row['coverage'])
            if identity(result)!=row['sha256'] or receipt.get('source_sha256')!=meta['sha256']:
                raise ValueError('Published version or receipt identity mismatch')
            rel=Path('raw')/safe_member(meta['ingestion_attempt']['relative_root'])/safe_member(meta['blob'])
            if str(rel) not in members:raise ValueError('Backup omits a published raw object')
            body=(directory/rel).read_bytes()
            if hashlib.sha256(body).hexdigest()!=meta['sha256']:raise ValueError('Published raw object hash mismatch')
        for row in db.execute('SELECT * FROM heads'):
            version=db.execute('SELECT stream,cycle FROM versions WHERE job_id=?',(row['job_id'],)).fetchone()
            newest=db.execute('SELECT max(cycle) FROM versions WHERE stream=?',(row['stream'],)).fetchone()[0]
            if version is None or version['stream']!=row['stream'] or version['cycle']!=newest:
                raise ValueError('Backup current pointer is missing, mismatched or regressed')
        if db.execute("SELECT id FROM jobs WHERE state='succeeded' AND id NOT IN (SELECT job_id FROM versions)").fetchone():
            raise ValueError('Successful job has no published version')
        if db.execute('SELECT stream FROM versions EXCEPT SELECT stream FROM heads').fetchone():
            raise ValueError('Published stream has no current pointer')


def backup(database, raw_root, output):
    """New portable SQLite snapshot plus hash-checked raw objects for committed versions."""
    import hashlib,os,shutil,tempfile
    output=Path(output).resolve();raw_root=Path(raw_root).resolve()
    if output.exists():raise FileExistsError('Backup destination must be new')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.backup-',dir=output.parent))
    try:
        from contextlib import closing
        with closing(sqlite3.connect(stage/'ingestion.sqlite')) as dest:database.db.backup(dest)
        with closing(sqlite3.connect(stage/'ingestion.sqlite')) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup SQLite integrity failed')
            for row in db.execute('SELECT result,sha256 FROM versions'):
                result=json.loads(row[0]);meta=result['provenance']
                if identity(result)!=row[1]:raise ValueError('Published version hash mismatch')
                rel=safe_member(meta['ingestion_attempt']['relative_root'])/safe_member(meta['blob'])
                src=(raw_root/rel).resolve()
                if raw_root not in src.parents:raise ValueError('Raw object path leaves configured root')
                body=src.read_bytes()
                if hashlib.sha256(body).hexdigest()!=meta['sha256']:raise ValueError('Raw object hash mismatch')
                target=stage/'raw'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
        files={str(p.relative_to(stage)):hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file()}
        validate_backup_content(stage,files)
        (stage/'backup-manifest.json').write_text(json.dumps({'schema_version':'ingestion-backup-v2','created_at':stamp(database.clock()),'files':files,
            'scope':'Queue state, published versions, coverage receipts and their raw payloads. Failed-attempt raw objects and request caches excluded.'},indent=2)+'\n')
        if output.exists():raise FileExistsError('Backup destination appeared concurrently')
        os.rename(stage,output)
        return {'directory':str(output),'files':len(files),'bytes':sum((output/p).stat().st_size for p in files)}
    except BaseException:
        shutil.rmtree(stage);raise


def restore(bundle, output):
    import hashlib,os,shutil,tempfile
    bundle=Path(bundle).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError('Restore destination must be new')
    manifest=json.loads((bundle/'backup-manifest.json').read_text())
    if not isinstance(manifest,dict) or manifest.get('schema_version') not in {None,'ingestion-backup-v2'}:
        raise ValueError('Unsupported backup manifest version')
    members=manifest.get('files')
    if not isinstance(members,dict) or 'ingestion.sqlite' not in members:
        raise ValueError('Backup must include ingestion.sqlite')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.restore-',dir=output.parent))
    try:
        for rel,sha in members.items():
            path=safe_member(rel)
            src=(bundle/path).resolve()
            if bundle not in src.parents:raise ValueError('Backup member leaves bundle')
            body=src.read_bytes()
            if hashlib.sha256(body).hexdigest()!=sha:raise ValueError('Backup member hash mismatch')
            dest=stage/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body)
        validate_backup_content(stage,members)
        if output.exists():raise FileExistsError('Restore destination appeared concurrently')
        os.rename(stage,output)
        return {'directory':str(output),'database':str(output/'ingestion.sqlite'),'raw_root':str(output/'raw')}
    except BaseException:
        shutil.rmtree(stage);raise
