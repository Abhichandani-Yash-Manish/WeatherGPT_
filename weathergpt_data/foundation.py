"""Public research/prototype data interface with explicit provenance and capability limits."""
import json,re,xml.etree.ElementTree as ET
from datetime import datetime,timedelta,timezone,date
from pathlib import Path
from urllib.parse import urlparse
from .transport import Store,SourceError,utcnow,stamp,parsed
from .adapters import json_payload,hourly,FORECAST,MARINE,RIVER,aviation,warnings,envelope,numeric,grid_identity,numeric_quality
from .adapters import EXTENDED,HISTORY_LOCAL,REANALYSIS_MODELS,reanalysis_fields,reanalysis_label
from .adapters import ENSEMBLE,ENSEMBLE_MODELS,ensemble
from .adapters import AIR_QUALITY,air_quality
from .adapters import (ERA5_HOURLY,PREVIOUS_RUNS,PREVIOUS_RUNS_MODELS,PREVIOUS_RUN_LEADS,
                       era5_hourly as era5_hourly_adapter,previous_runs as previous_runs_adapter)
from .verification import summarise as verification_summarise
ROOT=Path(__file__).resolve().parents[1]

class Foundation:
    def __init__(self,store=None):self.store=store or Store(ROOT/'data/runtime')
    def get(self,sid,url,params=None,product_parser=None,**kwargs):
        def validate(body,meta):
            try:product_parser(json_payload(body),meta)
            except (ValueError,TypeError,KeyError,IndexError,OverflowError) as exc:raise SourceError('Product validation failed: '+str(exc)) from exc
        body,meta=self.store.fetch(sid,url,params,validator=json_payload,product_validator=validate if product_parser else None,**kwargs)
        return json_payload(body),meta
    def forecast_dates(self,days,limit):
        if isinstance(days,bool) or not isinstance(days,int) or not 1<=days<=limit:raise SourceError(f'Request 1–{limit} whole days')
        start=self.store.clock().astimezone(timezone.utc).date()
        return start,start+timedelta(days=days-1)
    @staticmethod
    def point(lat,lon):
        if lat is None or lon is None:raise SourceError('Both numeric coordinates are required')
        return {'latitude':numeric(lat,-90,90),'longitude':numeric(lon,-180,180)}
    def forecast(self,lat,lon,days=3,refresh=False):
        point=self.point(lat,lon)
        self.forecast_dates(days,7)
        parse=lambda d,m:hourly(d,m,FORECAST,'weather_forecast','Open-Meteo GFS delivery; upstream run unspecified',point,self.forecast_dates(days,7))
        data,meta=self.get('S21','https://api.open-meteo.com/v1/gfs',{**point,'hourly':','.join(FORECAST),'forecast_days':days,'timezone':'UTC','timeformat':'unixtime','temperature_unit':'celsius','wind_speed_unit':'kmh','precipitation_unit':'mm'},refresh=refresh,product_parser=parse)
        return parse(data,meta)
    def marine(self,lat,lon,days=3,refresh=False):
        point=self.point(lat,lon)
        self.forecast_dates(days,7)
        parse=lambda d,m:hourly(d,m,MARINE,'marine_forecast','Open-Meteo default marine model selection; run unspecified',point,self.forecast_dates(days,7))
        data,meta=self.get('S56','https://marine-api.open-meteo.com/v1/marine',{**point,'hourly':','.join(MARINE),'forecast_days':days,'timezone':'UTC','timeformat':'unixtime','cell_selection':'sea'},refresh=refresh,ttl=3600,product_parser=parse)
        result=parse(data,meta)
        result['limitations']+=['Wave information is not an official marine warning or navigation clearance.','Requested inland/coastal points may be mapped to a different sea grid; inspect returned coordinates.']
        return result
    def extended_forecast(self,lat,lon,days=3,refresh=False):
        point=self.point(lat,lon)
        self.forecast_dates(days,7)
        parse=lambda d,m:hourly(d,m,EXTENDED,'extended_weather_forecast','Open-Meteo best match; variable-specific upstream model/run unspecified',point,self.forecast_dates(days,7))
        data,meta=self.get('S62','https://api.open-meteo.com/v1/forecast',{**point,'hourly':','.join(EXTENDED),'forecast_days':days,'timezone':'UTC','timeformat':'unixtime','temperature_unit':'celsius','wind_speed_unit':'kmh','precipitation_unit':'mm'},refresh=refresh,product_parser=parse)
        return parse(data,meta)
    def ensemble(self,lat,lon,days=3,model='gfs025',variables=None,threshold=None,refresh=False):
        """The member spread of one ensemble model for a point. Not a probability or a score."""
        point=self.point(lat,lon)
        self.forecast_dates(days,7)
        if model not in ENSEMBLE_MODELS:raise SourceError('Unsupported ensemble model: '+str(model))
        selected=tuple(variables) if variables else tuple(ENSEMBLE)
        if not selected or any(name not in ENSEMBLE for name in selected):raise SourceError('Unsupported ensemble variable')
        fields={name:ENSEMBLE[name] for name in selected}
        parse=lambda d,m:ensemble(d,m,fields,model,point,self.forecast_dates(days,7),threshold=threshold)
        data,meta=self.get('S68','https://ensemble-api.open-meteo.com/v1/ensemble',
                            {**point,'hourly':','.join(selected),'models':model,'forecast_days':days,
                             'timezone':'UTC','timeformat':'unixtime','temperature_unit':'celsius',
                             'wind_speed_unit':'kmh','precipitation_unit':'mm'},refresh=refresh,product_parser=parse)
        return parse(data,meta)
    def air_quality(self,lat,lon,days=3,variables=None,refresh=False):
        """Modelled pollutant concentrations and the source's own air-quality indices."""
        point=self.point(lat,lon)
        self.forecast_dates(days,7)
        selected=tuple(variables) if variables else tuple(AIR_QUALITY)
        if not selected or any(name not in AIR_QUALITY for name in selected):raise SourceError('Unsupported air-quality variable')
        fields={name:AIR_QUALITY[name] for name in selected}
        parse=lambda d,m:air_quality(d,m,fields,point,self.forecast_dates(days,7))
        data,meta=self.get('S69','https://air-quality-api.open-meteo.com/v1/air-quality',
                            {**point,'hourly':','.join(selected),'current':','.join(selected),
                             'forecast_days':days,'timezone':'UTC','timeformat':'unixtime'},refresh=refresh,product_parser=parse)
        return parse(data,meta)
    def _verification_window(self,start,end,label):
        a=date.fromisoformat(start);b=date.fromisoformat(end)
        if a>b or (b-a).days>30:raise SourceError(label+' supports one to thirty-one ordered completed days')
        today=self.store.clock().astimezone(timezone.utc).date()
        if b>today:raise SourceError(label+' needs completed dates; a future date is not a vintage')
        return a,b
    def previous_runs(self,lat,lon,start,end,model='gfs_seamless',variables=None,leads=None,refresh=False):
        """Archived model runs at fixed lead-time offsets, for verification only."""
        point=self.point(lat,lon);a,b=self._verification_window(start,end,'Previous-runs retrieval')
        if model not in PREVIOUS_RUNS_MODELS:raise SourceError('Unsupported previous-runs model: '+str(model))
        selected=tuple(variables) if variables else tuple(PREVIOUS_RUNS)
        chosen=tuple(leads) if leads else PREVIOUS_RUN_LEADS
        if any(name not in PREVIOUS_RUNS for name in selected) or any(lead not in PREVIOUS_RUN_LEADS for lead in chosen):
            raise SourceError('Unsupported previous-runs variable or lead time')
        fields={name:PREVIOUS_RUNS[name] for name in selected}
        columns=[name+'_previous_day%d'%lead for name in selected for lead in chosen]
        parse=lambda d,m:previous_runs_adapter(d,m,fields,model,chosen,point,(a,b))
        data,meta=self.get('S70','https://previous-runs-api.open-meteo.com/v1/forecast',
                            {**point,'hourly':','.join(columns),'models':model,'start_date':start,'end_date':end,
                             'timezone':'UTC','timeformat':'unixtime','temperature_unit':'celsius',
                             'precipitation_unit':'mm'},refresh=refresh,product_parser=parse)
        return parse(data,meta)
    def era5_hourly(self,lat,lon,start,end,variables=None,refresh=False):
        """ERA5 hourly reanalysis for a completed window. The verification reference, not an observation."""
        point=self.point(lat,lon);a,b=self._verification_window(start,end,'ERA5 hourly retrieval')
        today=self.store.clock().astimezone(timezone.utc).date()
        if (today-b).days<5:raise SourceError('ERA5 hourly is published with about a five-day delay; choose an earlier window')
        selected=tuple(variables) if variables else tuple(ERA5_HOURLY)
        if any(name not in ERA5_HOURLY for name in selected):raise SourceError('Unsupported ERA5 hourly variable')
        fields={name:ERA5_HOURLY[name] for name in selected}
        parse=lambda d,m:era5_hourly_adapter(d,m,fields,point,(a,b))
        data,meta=self.get('S22','https://archive-api.open-meteo.com/v1/archive',
                            {**point,'hourly':','.join(selected),'models':'era5','start_date':start,'end_date':end,
                             'timezone':'UTC','timeformat':'unixtime','temperature_unit':'celsius',
                             'precipitation_unit':'mm'},refresh=refresh,product_parser=parse)
        return parse(data,meta)
    def verification(self,lat,lon,start,end,model='gfs_seamless',variables=None,leads=None,refresh=False):
        """Measure archived runs against ERA5 reanalysis. A measurement, not an operational skill score."""
        forecast=self.previous_runs(lat,lon,start,end,model=model,variables=variables,leads=leads,refresh=refresh)
        reference=self.era5_hourly(lat,lon,start,end,variables=variables,refresh=refresh)
        result=verification_summarise(forecast,reference)
        for side,packet in (('forecast',forecast),('reference',reference)):
            result[side].update({'retrieved_at_utc':(packet.get('provenance') or {}).get('retrieved_at_utc'),
                                 'url':(packet.get('provenance') or {}).get('url')})
        result['window']={'start':start,'end':end}
        return result
    def history_local(self,lat,lon,start,end,refresh=False,models='era5'):
        point=self.point(lat,lon);a=date.fromisoformat(start);b=date.fromisoformat(end)
        if a>b or (b-a).days>6:raise SourceError('Local daily retrieval supports one to seven days per task')
        if models not in REANALYSIS_MODELS:raise SourceError('Unsupported reanalysis model: '+str(models))
        # Only the variables the selected model returns are requested. Asking for a variable a
        # model does not carry returns nulls, and a payload with null columns is not publishable.
        fields=reanalysis_fields(models)
        parse=lambda d,m:self.daily(d,m,point,fields,'reanalysis',reanalysis_label(models),(a,b),timezone_name='Asia/Kolkata')
        data,meta=self.get('S22','https://archive-api.open-meteo.com/v1/archive',{**point,'start_date':start,'end_date':end,'daily':','.join(fields),'models':models,'timezone':'Asia/Kolkata'},ttl=86400,refresh=refresh,product_parser=parse)
        return parse(data,meta)
    def aviation(self,ids,kind='metar',refresh=False):
        if kind not in ['metar','taf','stationinfo']:raise SourceError('Supported airport products: metar, taf, stationinfo')
        ids=[s.upper() for s in ids]
        if not 1<=len(ids)<=20 or any(not re.fullmatch('[A-Z]{4}',s) for s in ids):raise SourceError('Provide 1–20 four-letter ICAO station codes')
        params={'ids':','.join(ids),'format':'json'}
        if kind=='metar':params['hours']=3
        parse=lambda d,m:aviation(d,m,kind,ids,self.store.clock())
        data,meta=self.get({'metar':'S18','taf':'S19','stationinfo':'S20'}[kind],'https://aviationweather.gov/api/data/'+kind,params,refresh=refresh,ttl=300 if kind=='metar' else 3600,product_parser=parse)
        return parse(data,meta)
    def warning_snapshot(self,lat=None,lon=None,refresh=False):
        point=self.point(lat,lon) if lat is not None and lon is not None else None
        if (lat is None)!=(lon is None):raise SourceError('Both coordinates are required')
        parse=lambda d,m:warnings(d,m,self.store.clock(),point)
        data,meta=self.get('S15','https://reactjs.imd.gov.in/geoserver/wfs',{'service':'WFS','version':'1.1.0','request':'GetFeature','typename':'imd:district_warnings_india','srsname':'EPSG:4326','outputFormat':'application/json','maxFeatures':2000},max_bytes=50_000_000,refresh=refresh,ttl=900,product_parser=parse)
        return parse(data,meta)
    def history(self,lat,lon,start,end,refresh=False):
        point=self.point(lat,lon)
        try:a=date.fromisoformat(start);b=date.fromisoformat(end)
        except ValueError as exc:raise SourceError('Use YYYY-MM-DD dates') from exc
        if a>b or (b-a).days>366:raise SourceError('Request an ordered interval of at most 367 days; chunk longer periods explicitly')
        fields={'precipitation_sum':('mm',0),'temperature_2m_max':('°C',None),'temperature_2m_min':('°C',None)}
        parse=lambda d,m:self.daily(d,m,point,fields,'reanalysis','ERA5 via Open-Meteo',(a,b))
        data,meta=self.get('S22','https://archive-api.open-meteo.com/v1/archive',{**point,'start_date':start,'end_date':end,'daily':'precipitation_sum,temperature_2m_max,temperature_2m_min','models':'era5','timezone':'UTC'},ttl=86400,refresh=refresh,product_parser=parse)
        return parse(data,meta)
    def river(self,lat,lon,days=7,refresh=False):
        point=self.point(lat,lon)
        self.forecast_dates(days,30)
        parse=lambda d,m:self.daily(d,m,point,RIVER,'river_discharge','GloFAS default selection via Open-Meteo',self.forecast_dates(days,30))
        data,meta=self.get('S37','https://flood-api.open-meteo.com/v1/flood',{**point,'daily':'river_discharge','forecast_days':days},ttl=3600,refresh=refresh,product_parser=parse)
        result=parse(data,meta)
        result['limitations']+=['River-cell identity has not been matched to a local gauge.','Discharge does not describe inundation, damage or an official flood warning.']
        return result
    @staticmethod
    def daily(data,meta,point,fields,family,model,expected_dates=None,timezone_name='UTC'):
        from zoneinfo import ZoneInfo
        if timezone_name not in {'UTC','Asia/Kolkata'}:raise SourceError('Unsupported daily timezone')
        offset=19800 if timezone_name=='Asia/Kolkata' else 0
        if not isinstance(data,dict) or type(data.get('utc_offset_seconds')) not in {int,float} or data['utc_offset_seconds']!=offset:raise SourceError('Daily timezone offset mismatch')
        if timezone_name=='Asia/Kolkata' and data.get('timezone') not in {'Asia/Kolkata','Asia/Calcutta'}:raise SourceError('Daily timezone identity mismatch')
        grid=grid_identity(data)
        block=data.get('daily');units=data.get('daily_units')
        if not isinstance(block,dict) or not isinstance(units,dict):raise SourceError('Daily block and units must be objects')
        times=block.get('time')
        if not isinstance(times,list) or any(not isinstance(t,str) for t in times):raise SourceError('Daily time axis must contain ISO dates')
        dates=[date.fromisoformat(t) for t in times]
        if not dates or any(b-a!=timedelta(days=1) for a,b in zip(dates,dates[1:])):raise SourceError('Missing, duplicated or nonconsecutive daily dates')
        if expected_dates and (dates[0],dates[-1])!=expected_dates:raise SourceError('Incomplete requested history coverage')
        records=[]
        for field,spec in fields.items():
            unit,minimum=spec[0],spec[1]
            maximum=spec[2] if len(spec)>2 else None
            values=block.get(field)
            if units.get(field)!=unit or not isinstance(values,list) or len(values)!=len(times):raise SourceError('Daily units/schema mismatch')
            for i,(d,value) in enumerate(zip(dates,values)):
                v=numeric(value,minimum,maximum)
                start=datetime.combine(d,datetime.min.time(),ZoneInfo(timezone_name))
                if any(t.utcoffset().total_seconds()!=offset for t in [start,start+timedelta(days=1)]):raise SourceError('Historical timezone offset differs from the returned daily offset; this local-day contract cannot resolve it')
                records.append({'date':d.isoformat(),'period_start_utc':stamp(start),'period_end_utc':stamp(start+timedelta(days=1)),'parameter':field,'value':v,'unit':unit,'model':model,'quality_flags':['source_value_missing'] if v is None else [],'source_locator':f'$.daily.{field}[{i}]'})
        result=envelope(family,meta['source_id'],records,meta,['Model-derived daily data; not direct gauge measurements.'],{'requested_point':point,'returned_grid':grid,'time_basis':timezone_name})
        return numeric_quality(result,expected_dates is not None)
    def places(self,name,refresh=False):
        if not isinstance(name,str) or not 2<=len(name)<=100:raise SourceError('Place name must contain 2–100 characters')
        def validate_places(data,meta):
            if not isinstance(data,dict):raise SourceError('Place response must be an object')
            records=data.get('results',[])
            if not isinstance(records,list):raise SourceError('Place results must be a list')
            if 'results' not in data and (numeric(data.get('generationtime_ms'),0) is None):raise SourceError('Missing place-result schema')
            ids=set()
            for r in records:
                if not isinstance(r,dict) or type(r.get('id')) is not int or not isinstance(r.get('name'),str) or not r['name'].strip():raise SourceError('Invalid place identity')
                if r['id'] in ids:raise SourceError('Duplicate place identity')
                ids.add(r['id']);self.point(r.get('latitude'),r.get('longitude'))
                if r.get('country_code')!='IN':raise SourceError('Place result is outside requested country')
        data,meta=self.get('S24','https://geocoding-api.open-meteo.com/v1/search',{'name':name,'count':10,'language':'en','format':'json','countryCode':'IN'},ttl=86400,refresh=refresh,product_parser=validate_places)
        records=data.get('results',[])
        result=envelope('place_candidates','S24',records,meta,['User/application must select a candidate; place ID is not a station or district code.'])
        if len(records)>1:result['status']='needs_selection'
        return result
    def cap(self,refresh=False):
        def rss(raw,meta):
            try:root=ET.fromstring(raw)
            except ET.ParseError as exc:raise SourceError('Invalid RSS') from exc
            if root.tag!='rss' or root.find('channel') is None:raise SourceError('Expected RSS channel')
            return root
        body,meta=self.store.fetch('S06','https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml',ttl=900,refresh=refresh,product_validator=rss)
        root=rss(body,meta);items=root.findall('./channel/item')
        records=[];errors=[]
        for item in items[:20]:
            link=item.findtext('link','');u=urlparse(link)
            if u.scheme!='https' or u.netloc!='cap-sources.s3.amazonaws.com' or not u.path.startswith('/in-imd-en/') or not u.path.endswith('.xml'):
                errors.append({'reason':'Unexpected CAP link'});continue
            try:
                raw,m=self.store.fetch('S06',link,ttl=3600,refresh=refresh,max_bytes=2_000_000,product_validator=lambda b,m:parse_cap(b,m,self.store.clock()))
                record=parse_cap(raw,m,self.store.clock());records.append(record)
            except (SourceError,ET.ParseError,ValueError) as exc:errors.append({'url':link,'reason':str(exc)})
        result=envelope('official_cap_messages','S06',records,meta,['Feed completeness and geographic coverage are unverified; no active message is not an all-clear.','Use msgType/references and per-language area/validity fields before dissemination.'],{'message_errors':errors,'feed_item_count':len(items),'attempted_item_count':min(20,len(items)),'omitted_item_count':max(0,len(items)-20),'feed_items_complete':len(items)<=20 and not errors})
        result['status']='reference_only' if records else 'unknown_coverage'
        from .cap_lifecycle import resolve
        lifecycle=resolve(records,self.store.clock())
        result['records']=lifecycle['records'];result['lifecycle_assessment']={k:v for k,v in lifecycle.items() if k!='records'}
        result['actionable_current_alerts']=False
        result['limitations'].append('CAP reference chains are resolved only within the retrieved feed. Missing parents, conflicts and forks are held. Geographic applicability, origin authenticity and feed completeness remain unverified; lifecycle eligibility is not dissemination eligibility.')
        if errors or len(items)>20:result['status']='partial' if records else 'unavailable'
        return result

def parse_cap(raw,meta,now):
    try:root=ET.fromstring(raw)
    except ET.ParseError as exc:raise SourceError('Invalid CAP XML') from exc
    ns={'c':'urn:oasis:names:tc:emergency:cap:1.2'}
    def value(name,node=root):return node.findtext('c:'+name,default='',namespaces=ns)
    if root.tag!='{urn:oasis:names:tc:emergency:cap:1.2}alert':raise SourceError('Unsupported CAP namespace/root')
    identifier=value('identifier');sent=value('sent');status=value('status');msg=value('msgType')
    if not identifier or not sent or msg not in ['Alert','Update','Cancel','Ack','Error']:raise SourceError('Invalid CAP identity/lifecycle')
    if not value('sender') or status not in {'Actual','Exercise','System','Test','Draft'} or value('scope') not in {'Public','Restricted','Private'}:raise SourceError('Invalid CAP sender, status or scope')
    if msg in {'Update','Cancel'} and not value('references').strip():raise SourceError('CAP update/cancel lacks referenced message identity')
    if parsed(sent)>now+timedelta(minutes=10):raise SourceError('Future CAP sent time')
    infos=[]
    for info in root.findall('c:info',ns):
        effective=value('effective',info) or sent;expires=value('expires',info)
        effective_time=parsed(effective)
        if expires and parsed(expires)<=effective_time:raise SourceError('CAP expiry must follow effective time')
        active=status=='Actual' and value('scope')=='Public' and msg in ['Alert','Update'] and bool(expires) and effective_time<=now<parsed(expires)
        areas=[{'description':value('areaDesc',a),'polygons':[e.text for e in a.findall('c:polygon',ns)],'circles':[e.text for e in a.findall('c:circle',ns)],'geocodes':[{c.tag.split('}')[-1]:c.text for c in g} for g in a.findall('c:geocode',ns)]} for a in info.findall('c:area',ns)]
        infos.append({'language':value('language',info) or 'en-US','event':value('event',info),'headline':value('headline',info),'description':value('description',info),'instruction':value('instruction',info),'severity':value('severity',info),'urgency':value('urgency',info),'certainty':value('certainty',info),'effective':effective,'expires':expires or None,'active_by_time_and_status':active,'areas':areas})
    return {'identifier':identifier,'sender':value('sender'),'sent':sent,'status':status,'msg_type':msg,'scope':value('scope'),'references':value('references'),'info':infos,'provenance':meta,'geographic_applicability':'Not established by time/status alone.'}
