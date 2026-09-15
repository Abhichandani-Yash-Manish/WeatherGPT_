"""Bounded public GETs, immutable response blobs, request cache and explicit stale fallback."""
import hashlib,json,time,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlencode,urlparse

class SourceError(ValueError):
    def __init__(self,message,*,retryable=False,retry_at=None,http_status=None,deferred=False):
        super().__init__(message)
        self.retryable=retryable;self.retry_at=retry_at;self.http_status=http_status;self.deferred=deferred

def utcnow():return datetime.now(timezone.utc)
def stamp(value):return value.astimezone(timezone.utc).isoformat()
def parsed(value):
    if not isinstance(value,str):raise SourceError('Timestamp must be a string with a timezone')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise SourceError('Timestamp must specify its timezone')
    return result
def align_source_day(start,end):
    """Read a midnight-to-midnight IST calendar day as the source's own day, and say so.

    Source hours start at :30 IST, so a 00:00-to-00:00 window contains 23 complete hours and
    a whole-day question comes back reduced for a reason the user did not ask about. The
    returned note is meant to be shown; the window is returned unchanged in every other case.
    """
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    start,end=parsed(start) if isinstance(start,str) else start,parsed(end) if isinstance(end,str) else end
    ist=ZoneInfo('Asia/Kolkata')
    local_start,local_end=start.astimezone(ist),end.astimezone(ist)
    if (local_start.strftime('%H:%M'),local_end.strftime('%H:%M'))==('00:00','00:00') and \
       local_end-local_start==timedelta(days=1):
        shifted_start,shifted_end=local_start+timedelta(minutes=30),local_end+timedelta(minutes=30)
        return (shifted_start,shifted_end,
                'The day was asked for as midnight to midnight IST; source hours start at :30 IST, so it is read as '
                +shifted_start.strftime('%d %b %Y %H:%M')+' to '+shifted_end.strftime('%d %b %Y %H:%M')+' IST.')
    return start,end,None


def digest(data):return hashlib.sha256(data).hexdigest()
def write_json(path,value):
    import os,tempfile
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.tmp-')
    try:
        with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
        os.replace(tmp,path)
    finally:
        if Path(tmp).exists():Path(tmp).unlink()

class Store:
    def __init__(self,root,opener=None,clock=utcnow):
        self.root=Path(root);self.opener=opener or urllib.request.urlopen;self.clock=clock
    def _load(self,item):
        path=(self.root/item['blob']).resolve()
        if self.root.resolve() not in path.parents:raise SourceError('Cached blob path leaves store')
        data=path.read_bytes()
        if digest(data)!=item['sha256']:raise SourceError('Cached response hash mismatch')
        return data
    def fetch(self,source_id,url,params=None,ttl=900,max_bytes=12_000_000,refresh=False,validator=None,product_validator=None):
        """Validate every delivery; publish only accepted responses. Lock each request across processes."""
        from .filelock import try_lock_exclusive,unlock
        if params:url+='?'+urlencode(params)
        u=urlparse(url)
        if u.scheme!='https' or u.username or u.password:raise SourceError('Only credential-free HTTPS sources supported')
        key=digest((source_id+'|'+url).encode())
        locks=self.root/'locks';locks.mkdir(parents=True,exist_ok=True)
        with (locks/(key+'.lock')).open('a') as lock:
            try_lock_exclusive(lock)
            try:return self._fetch_locked(source_id,url,key,ttl,max_bytes,refresh,validator,product_validator)
            finally:unlock(lock)

    def _fetch_locked(self,source_id,url,key,ttl,max_bytes,refresh,validator,product_validator):
        index=self.root/'cache'/(key+'.json');now=self.clock()
        def validate(data,meta):
            if validator is not None:validator(data)
            if product_validator is not None:product_validator(data,meta)
        def event(item):write_json(self.root/'events'/(key+'-'+str(time.time_ns())+'.json'),item)
        previous=None
        if index.exists():
            try:
                candidate_index=json.loads(index.read_text())
                if not isinstance(candidate_index,dict) or candidate_index.get('source_id')!=source_id or candidate_index.get('url')!=url:
                    raise SourceError('Cache request identity mismatch')
                if not isinstance(candidate_index.get('blob'),str) or not isinstance(candidate_index.get('sha256'),str):
                    raise SourceError('Missing cache blob identity')
                if parsed(candidate_index['retrieved_at_utc'])>now:raise SourceError('Cache retrieval time is in the future')
                previous=candidate_index
            except (ValueError,TypeError,KeyError,OSError) as exc:
                event({'stage':'cache_index_rejected','source_id':source_id,'url':url,'checked_at_utc':stamp(now),'error':str(exc)})
        previous_data=None;previous_error=None
        if previous:
            try:
                previous_data=self._load(previous)
                validate(previous_data,{**previous,'delivery':'cache','checked_at_utc':stamp(now)})
            except (ValueError,TypeError,KeyError,IndexError,OverflowError,OSError) as exc:
                previous_data=None;previous_error=str(exc)
                event({'stage':'cached_rejected','source_id':source_id,'url':url,'checked_at_utc':stamp(now),'error':str(exc),'sha256':previous.get('sha256')})
        if previous_data is not None and not refresh and 0<=(now-parsed(previous['retrieved_at_utc'])).total_seconds()<=ttl:
            return previous_data,{**previous,'delivery':'cache','checked_at_utc':stamp(now)}
        candidate=None
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'WeatherGPT-research-foundation/1.1','Accept':'application/json,application/xml,text/html,application/pdf,*/*'})
            with self.opener(request,timeout=25) as response:
                status=response.status;data=response.read(max_bytes+1);ctype=response.headers.get('Content-Type','')
            if len(data)>max_bytes:raise SourceError('Response exceeds configured size limit')
            if status!=200:raise SourceError(f'HTTP {status}')
            hash_=digest(data);blob=Path('blobs')/(hash_+'.bin');target=self.root/blob;target.parent.mkdir(parents=True,exist_ok=True)
            # Publish complete immutable bytes via atomic hard link; never overwrite another writer's blob.
            import os,tempfile
            if not target.exists():
                fd,tmp=tempfile.mkstemp(dir=target.parent,prefix='.blob-')
                try:
                    with os.fdopen(fd,'wb') as f:f.write(data)
                    try:os.link(tmp,target)
                    except FileExistsError:pass
                finally:Path(tmp).unlink()
            if digest(target.read_bytes())!=hash_:raise SourceError('Stored response hash mismatch')
            candidate={'source_id':source_id,'url':url,'retrieved_at_utc':stamp(self.clock()),'http_status':status,'content_type':ctype,'bytes':len(data),'sha256':hash_,'blob':str(blob),'validation_scope':'product' if product_validator else ('payload' if validator else 'transport_only')}
            validate(data,{**candidate,'delivery':'network','checked_at_utc':stamp(self.clock())})
            event({**candidate,'stage':'validated' if validator or product_validator else 'downloaded'})
            write_json(index,candidate)
            return data,{**candidate,'delivery':'network','checked_at_utc':stamp(self.clock())}
        except (urllib.error.URLError,TimeoutError,OSError,ValueError,TypeError,KeyError,IndexError,OverflowError) as exc:
            error={'source_id':source_id,'url':url,'checked_at_utc':stamp(self.clock()),'stage':'rejected' if candidate else 'fetch_failed','error':str(exc),'error_type':type(exc).__name__}
            details={k:getattr(exc,k,default) for k,default in [('retryable',False),('retry_at',None),('http_status',None),('deferred',False)]}
            error.update(details)
            if candidate:error['rejected_response']=candidate
            if previous_error:error['previous_rejection']=previous_error
            event(error)
            if previous_data is not None:
                fallback={**previous,'delivery':'stale_cache','last_error':error,'checked_at_utc':stamp(self.clock())}
                # A request can straddle midnight or validity expiry during the network attempt.
                try:validate(previous_data,fallback)
                except (ValueError,TypeError,KeyError,IndexError,OverflowError) as invalid:raise SourceError('No cached data satisfies the current request: '+str(invalid)) from invalid
                return previous_data,fallback
            raise SourceError(str(exc),**details) from exc
