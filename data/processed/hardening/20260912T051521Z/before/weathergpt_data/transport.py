"""Bounded public GETs, immutable response blobs, request cache and explicit stale fallback."""
import hashlib,json,time,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlencode,urlparse

class SourceError(ValueError):pass

def utcnow():return datetime.now(timezone.utc)
def stamp(value):return value.astimezone(timezone.utc).isoformat()
def parsed(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise SourceError('Timestamp must specify its timezone')
    return result
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
        data=(self.root/item['blob']).read_bytes()
        if digest(data)!=item['sha256']:raise SourceError('Cached response hash mismatch')
        return data
    def fetch(self,source_id,url,params=None,ttl=900,max_bytes=12_000_000,refresh=False,validator=None):
        if params:url+='?'+urlencode(params)
        u=urlparse(url)
        if u.scheme!='https' or u.username or u.password:raise SourceError('Only credential-free HTTPS sources supported')
        key=digest((source_id+'|'+url).encode());index=self.root/'cache'/(key+'.json');now=self.clock()
        previous=json.loads(index.read_text()) if index.exists() else None
        if previous and not refresh and 0<=(now-parsed(previous['retrieved_at_utc'])).total_seconds()<=ttl:
            return self._load(previous),{**previous,'delivery':'cache','checked_at_utc':stamp(now)}
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'WeatherGPT-research-foundation/1.0','Accept':'application/json,application/xml,text/html,application/pdf,*/*'})
            with self.opener(request,timeout=25) as response:
                status=response.status;data=response.read(max_bytes+1);ctype=response.headers.get('Content-Type','')
            if len(data)>max_bytes:raise SourceError('Response exceeds configured size limit')
            if status!=200:raise SourceError(f'HTTP {status}')
            if validator is not None:validator(data)
            hash_=digest(data);blob=Path('blobs')/(hash_+'.bin');(self.root/blob).parent.mkdir(parents=True,exist_ok=True)
            if not (self.root/blob).exists():(self.root/blob).write_bytes(data)
            item={'source_id':source_id,'url':url,'retrieved_at_utc':stamp(self.clock()),'http_status':status,'content_type':ctype,'bytes':len(data),'sha256':hash_,'blob':str(blob)}
            event=self.root/'events'/(key+'-'+str(time.time_ns())+'.json');write_json(event,item);write_json(index,item)
            return data,{**item,'delivery':'network','checked_at_utc':stamp(self.clock())}
        except (urllib.error.URLError,TimeoutError,OSError,SourceError) as exc:
            error={'source_id':source_id,'url':url,'checked_at_utc':stamp(self.clock()),'error':str(exc),'error_type':type(exc).__name__}
            write_json(self.root/'events'/(key+'-'+str(time.time_ns())+'.json'),error)
            if previous:return self._load(previous),{**previous,**{'delivery':'stale_cache','last_error':error,'checked_at_utc':stamp(self.clock())}}
            raise SourceError(str(exc)) from exc
