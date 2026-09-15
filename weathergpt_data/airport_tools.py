"""Airport-specific NOAA/AWC evidence using the existing validated adapters."""
import json,re,urllib.request,urllib.error
from contextlib import contextmanager
from datetime import timedelta
from urllib.parse import urlparse,parse_qs
from .foundation import Foundation,ROOT
from .ingestion import IngestionDB,NoRedirect,retry_after,epoch
from .transport import Store,SourceError,parsed,stamp


class AirportOpener:
    def __init__(self,db,station,kind,opener=None):
        self.db=db;self.station=station;self.kind=kind;self.opener=opener or urllib.request.build_opener(NoRedirect()).open
    @contextmanager
    def __call__(self,request,timeout=25):
        url=urlparse(request.full_url);params={'ids':[self.station],'format':['json']}
        if self.kind=='metar':params['hours']=['3']
        if url.scheme!='https' or url.netloc!='aviationweather.gov' or url.path!='/api/data/'+self.kind or parse_qs(url.query)!=params or request.get_method()!='GET':raise SourceError('Airport request exceeds its fixed source contract')
        lock=self.db.path.with_suffix('.aviation-network.lock').open('a')
        try:
            from .filelock import try_lock_exclusive
            try_lock_exclusive(lock)
        except BlockingIOError:lock.close();raise SourceError('Another airport retrieval is in progress; retry shortly')
        try:rid=self.db.reserve(provider='aviationweather',limits=((60,12),(3600,100),(86400,300)))
        except BaseException:lock.close();raise
        cooldown=None
        try:
            with self.opener(request,timeout=timeout) as response:yield response
        except urllib.error.HTTPError as exc:
            if exc.code==429 or exc.code>=500:cooldown=max(retry_after(exc.headers.get('Retry-After') if exc.headers else None,self.db.clock()) or 0,epoch(self.db.clock())+60)
            raise SourceError('Airport source HTTP '+str(exc.code)) from exc
        finally:
            try:self.db.release(rid,cooldown)
            finally:lock.close()


def fetch(workspace,station,kind):
    sid={'metar':'S18','taf':'S19','stationinfo':'S20'}[kind]
    registry=json.loads(workspace.service.registry_path.read_text())
    entry=next((s for s in registry['products'] if s['id']==sid),{})
    if entry.get('integration',{}).get('status')!='prototype_adapter_tested':raise SourceError('Airport source is not enabled for this prototype')
    db=IngestionDB(workspace.service.ingestion_database,clock=workspace.clock)
    try:
        store=Store(workspace.service.raw_root.parent/'airport-evidence',clock=workspace.clock,opener=AirportOpener(db,station,kind,workspace.opener))
        packet=Foundation(store).aviation([station],kind)
        if packet['provenance']['delivery']=='stale_cache':raise SourceError('Airport refresh failed; cached reports excluded')
        if packet['status']!='ok' or not packet['records']:raise SourceError('No complete, current airport '+kind+' evidence is available')
        return packet
    finally:db.close()


def execute_airport(engine,result,plan,task):
    names=[p['name'].upper() for p in plan['places']]
    if not names or any(not re.fullmatch('V[A-Z]{3}',n) for n in names):
        result.update(answer='Which Indian airport? Give its four-letter ICAO code, such as VAAH for Ahmedabad airport. An airport report cannot stand in for conditions across a city.',follow_up='Four-letter ICAO airport code');return result
    if 'metar' in task['parameters'] and plan.get('start_local'):
        result.update(status='unavailable',answer='METAR reports current or recent airport observations. A requested future or historical window needs a different product; it cannot be answered with the latest report.')
        return result
    requested=task['parameters'];unsupported=[p for p in requested if p not in {'metar','taf'}]
    if unsupported and not set(requested)&{'metar','taf'}:
        result.update(status='unavailable',answer='I cannot retrieve flight status, cancellations or delays from the weather sources. Airport observations and TAF cannot establish whether your flight will operate; check the airline for that outcome.')
        return result
    if not requested or len(names)>2:raise SourceError('Request one or two airports and METAR or TAF')
    missing=list(unsupported);result['airport_reports']=[]
    for name in names:
        try:
            station=fetch(engine.workspace,name,'stationinfo');s=station['records'][0]
            if s['country']!='IN' or s['latitude'] is None or s['longitude'] is None:raise SourceError('Station is not a verified Indian airport point')
            for kind in requested:
                if kind not in {'metar','taf'}:continue
                packet=fetch(engine.workspace,name,kind);meta=packet['provenance'];cid='c-'+meta['sha256'];now=engine.workspace.clock()
                records=packet['records'] if kind=='metar' else [r for r in packet['records'] if parsed(r['valid_start_utc'])<=now<parsed(r['valid_end_utc'])]
                if not records:raise SourceError('No currently valid airport report')
                record=max(records,key=lambda r:parsed(r['observed_at_utc'] if kind=='metar' else r['valid_start_utc']))
                if kind=='metar':
                    at=parsed(record['observed_at_utc']);expiry=min(at+timedelta(hours=2),parsed(meta['retrieved_at_utc'])+timedelta(minutes=5))
                    if expiry<=now:raise SourceError('Airport observation is stale')
                else:
                    at=parsed(record['valid_start_utc']);expiry=min(parsed(record['valid_end_utc']),parsed(meta['retrieved_at_utc'])+timedelta(hours=1))
                    if plan.get('start_local') and (parsed(plan['start_local'])<at or parsed(plan['end_local'])>parsed(record['valid_end_utc'])):raise SourceError('TAF does not cover the whole requested period')
                result['citations'].append({'id':cid,'source_id':packet['source_id'],'provider':'NOAA Aviation Weather Center','product':name+' '+kind.upper(),'url':meta['url'],'response_sha256':meta['sha256'],'retrieved_at_utc':meta['retrieved_at_utc']})
                sm=station['provenance'];result['citations'].append({'id':'c-'+sm['sha256'],'source_id':'S20','provider':'NOAA Aviation Weather Center','product':name+' station identity','url':sm['url'],'response_sha256':sm['sha256'],'retrieved_at_utc':sm['retrieved_at_utc']})
                result['airport_reports'].append({'station':name,'kind':kind,'raw_report':record['raw_report'],'source_locator':record['source_locator'],'citation_ids':[cid],'observed_at':stamp(at) if kind=='metar' else None,'valid_start':stamp(at) if kind=='taf' else None,'valid_end':record.get('valid_end_utc')})
                if kind=='metar':
                    for parameter,label,unit in [('temperature_c','Airport temperature','°C'),('wind_speed_kt','Airport wind speed','kt')]:
                        value=record[parameter]
                        if value is None:missing.append(name+' '+parameter+' not reported');continue
                        result['facts'].append({'id':'f'+str(len(result['facts'])+1),'parameter':parameter,'label':label,'value':str(value),'unit':unit,
                            'place':name+' · '+str(s['name']),'entity_id':'icao:'+name,'observed_at':stamp(at),'start':stamp(at),'end':stamp(at),'sample_at':stamp(at),
                            'source_id':packet['source_id'],'evidence_kind':'observation','evidence_version':meta['sha256'],'citation_ids':[cid,'c-'+sm['sha256']],
                            'source_locators':[record['source_locator']+'.'+{'temperature_c':'temp','wind_speed_kt':'wspd'}[parameter]],'method':'reported_airport_observation'})
                result['expires_at_utc']=stamp(min(expiry,parsed(result['expires_at_utc']))) if result['expires_at_utc'] else stamp(expiry)
                result['trace']['tools'].append({'name':'airport_'+kind,'station':name,'source_id':packet['source_id'],'status':'retrieved','response_sha256':meta['sha256']})
        except (ValueError,OSError) as exc:missing.append(name+': '+str(exc))
    result['notes']+=missing+['Airport reports concern their stated station and validity. No flight status, operational clearance or city-wide weather is inferred.']
    result['status']='partial' if missing and (result['facts'] or result['airport_reports']) else 'answered' if result['facts'] or result['airport_reports'] else 'unavailable'
    result['answer']='\n'.join(r['station']+' '+r['kind'].upper()+': '+r['raw_report'] for r in result['airport_reports']) or 'No current airport evidence was retrieved. '+' '.join(missing)
    return result
