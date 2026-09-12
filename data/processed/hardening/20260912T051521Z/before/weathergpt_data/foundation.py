"""Public research/prototype data interface with explicit provenance and capability limits."""
import json,re,xml.etree.ElementTree as ET
from datetime import datetime,timedelta,timezone,date
from pathlib import Path
from urllib.parse import urlparse
from .transport import Store,SourceError,utcnow,stamp,parsed
from .adapters import json_payload,hourly,FORECAST,MARINE,aviation,warnings,envelope,numeric
ROOT=Path(__file__).resolve().parents[1]

class Foundation:
    def __init__(self,store=None):self.store=store or Store(ROOT/'data/runtime')
    def get(self,sid,url,params=None,**kwargs):
        body,meta=self.store.fetch(sid,url,params,validator=json_payload,**kwargs);return json_payload(body),meta
    @staticmethod
    def point(lat,lon):
        if lat is None or lon is None:raise SourceError('Both numeric coordinates are required')
        return {'latitude':numeric(lat,-90,90),'longitude':numeric(lon,-180,180)}
    def forecast(self,lat,lon,days=3,refresh=False):
        point=self.point(lat,lon)
        if not 1<=days<=7:raise SourceError('Prototype forecast requests support 1–7 days')
        data,meta=self.get('S21','https://api.open-meteo.com/v1/gfs',{**point,'hourly':','.join(FORECAST),'forecast_days':days,'timezone':'UTC','timeformat':'unixtime','temperature_unit':'celsius','wind_speed_unit':'kmh','precipitation_unit':'mm'},refresh=refresh)
        return hourly(data,meta,FORECAST,'weather_forecast','Open-Meteo GFS delivery; upstream run unspecified',point)
    def marine(self,lat,lon,days=3,refresh=False):
        point=self.point(lat,lon)
        if not 1<=days<=7:raise SourceError('Prototype marine requests support 1–7 days')
        data,meta=self.get('S56','https://marine-api.open-meteo.com/v1/marine',{**point,'hourly':','.join(MARINE),'forecast_days':days,'timezone':'UTC','timeformat':'unixtime','cell_selection':'sea'},refresh=refresh,ttl=3600)
        result=hourly(data,meta,MARINE,'marine_forecast','Open-Meteo default marine model selection; run unspecified',point)
        result['limitations']+=['Wave information is not an official marine warning or navigation clearance.','Requested inland/coastal points may be mapped to a different sea grid; inspect returned coordinates.']
        return result
    def aviation(self,ids,kind='metar',refresh=False):
        if kind not in ['metar','taf','stationinfo']:raise SourceError('Supported airport products: metar, taf, stationinfo')
        ids=[s.upper() for s in ids]
        if not 1<=len(ids)<=20 or any(not re.fullmatch('[A-Z]{4}',s) for s in ids):raise SourceError('Provide 1–20 four-letter ICAO station codes')
        params={'ids':','.join(ids),'format':'json'}
        if kind=='metar':params['hours']=3
        data,meta=self.get({'metar':'S18','taf':'S19','stationinfo':'S20'}[kind],'https://aviationweather.gov/api/data/'+kind,params,refresh=refresh,ttl=300 if kind=='metar' else 3600)
        return aviation(data,meta,kind,ids,self.store.clock())
    def warning_snapshot(self,lat=None,lon=None,refresh=False):
        point=self.point(lat,lon) if lat is not None and lon is not None else None
        if (lat is None)!=(lon is None):raise SourceError('Both coordinates are required')
        data,meta=self.get('S15','https://reactjs.imd.gov.in/geoserver/wfs',{'service':'WFS','version':'1.1.0','request':'GetFeature','typename':'imd:district_warnings_india','srsname':'EPSG:4326','outputFormat':'application/json','maxFeatures':2000},max_bytes=50_000_000,refresh=refresh,ttl=900)
        return warnings(data,meta,self.store.clock(),point)
    def history(self,lat,lon,start,end,refresh=False):
        point=self.point(lat,lon)
        try:a=date.fromisoformat(start);b=date.fromisoformat(end)
        except ValueError as exc:raise SourceError('Use YYYY-MM-DD dates') from exc
        if a>b or (b-a).days>366:raise SourceError('Request an ordered interval of at most 367 days; chunk longer periods explicitly')
        data,meta=self.get('S22','https://archive-api.open-meteo.com/v1/archive',{**point,'start_date':start,'end_date':end,'daily':'precipitation_sum,temperature_2m_max,temperature_2m_min','models':'era5','timezone':'UTC'},ttl=86400,refresh=refresh)
        return self.daily(data,meta,point,{'precipitation_sum':('mm',0),'temperature_2m_max':('°C',None),'temperature_2m_min':('°C',None)},'reanalysis','ERA5 via Open-Meteo',expected_dates=(a,b))
    def river(self,lat,lon,days=7,refresh=False):
        point=self.point(lat,lon)
        if not 1<=days<=30:raise SourceError('Request 1–30 days')
        data,meta=self.get('S37','https://flood-api.open-meteo.com/v1/flood',{**point,'daily':'river_discharge','forecast_days':days},ttl=3600,refresh=refresh)
        result=self.daily(data,meta,point,{'river_discharge':('m³/s',0)},'river_discharge','GloFAS default selection via Open-Meteo')
        result['limitations']+=['River-cell identity has not been matched to a local gauge.','Discharge does not describe inundation, damage or an official flood warning.']
        return result
    @staticmethod
    def daily(data,meta,point,fields,family,model,expected_dates=None):
        if not isinstance(data,dict) or data.get('utc_offset_seconds',0)!=0:raise SourceError('Expected single-location UTC daily result')
        block=data.get('daily',{});units=data.get('daily_units',{});times=block.get('time',[])
        dates=[date.fromisoformat(t) for t in times]
        if not dates or any(b-a!=timedelta(days=1) for a,b in zip(dates,dates[1:])):raise SourceError('Missing, duplicated or nonconsecutive daily dates')
        if expected_dates and (dates[0],dates[-1])!=expected_dates:raise SourceError('Incomplete requested history coverage')
        records=[]
        for field,(unit,minimum) in fields.items():
            values=block.get(field)
            if units.get(field)!=unit or not isinstance(values,list) or len(values)!=len(times):raise SourceError('Daily units/schema mismatch')
            for i,(d,value) in enumerate(zip(dates,values)):
                v=numeric(value,minimum)
                records.append({'date':d.isoformat(),'period_start_utc':d.isoformat()+'T00:00:00+00:00','period_end_utc':(d+timedelta(days=1)).isoformat()+'T00:00:00+00:00','parameter':field,'value':v,'unit':unit,'model':model,'quality_flags':['source_value_missing'] if v is None else [],'source_locator':f'$.daily.{field}[{i}]'})
        result=envelope(family,meta['source_id'],records,meta,['Model-derived daily data; not direct gauge measurements.'],{'requested_point':point,'returned_grid':{'latitude':data.get('latitude'),'longitude':data.get('longitude')},'time_basis':'UTC'})
        if not any(r['value'] is not None for r in records):result['status']='no_data'
        return result
    def places(self,name,refresh=False):
        if not isinstance(name,str) or not 2<=len(name)<=100:raise SourceError('Place name must contain 2–100 characters')
        data,meta=self.get('S24','https://geocoding-api.open-meteo.com/v1/search',{'name':name,'count':10,'language':'en','format':'json','countryCode':'IN'},ttl=86400,refresh=refresh)
        records=[r for r in data.get('results',[]) if r.get('country_code')=='IN']
        result=envelope('place_candidates','S24',records,meta,['User/application must select a candidate; place ID is not a station or district code.'])
        if len(records)>1:result['status']='needs_selection'
        return result
    def cap(self,refresh=False):
        body,meta=self.store.fetch('S06','https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml',ttl=900,refresh=refresh)
        try:root=ET.fromstring(body)
        except ET.ParseError as exc:raise SourceError('Invalid RSS') from exc
        records=[];errors=[]
        for item in root.findall('.//item')[:20]:
            link=item.findtext('link','');u=urlparse(link)
            if u.scheme!='https' or u.netloc!='cap-sources.s3.amazonaws.com' or not u.path.startswith('/in-imd-en/') or not u.path.endswith('.xml'):
                errors.append({'reason':'Unexpected CAP link'});continue
            try:
                raw,m=self.store.fetch('S06',link,ttl=3600,refresh=refresh,max_bytes=2_000_000)
                record=parse_cap(raw,m,self.store.clock());records.append(record)
            except (SourceError,ET.ParseError,ValueError) as exc:errors.append({'url':link,'reason':str(exc)})
        result=envelope('official_cap_messages','S06',records,meta,['Feed completeness and geographic coverage are unverified; no active message is not an all-clear.','Use msgType/references and per-language area/validity fields before dissemination.'],{'message_errors':errors})
        result['status']='reference_only' if records else 'unknown_coverage'
        result['actionable_current_alerts']=False
        result['limitations'].append('CAP update/cancel chains and geographic applicability have not been resolved; time/status eligibility is not dissemination eligibility.')
        if errors:result['status']='partial' if records else 'unavailable'
        return result

def parse_cap(raw,meta,now):
    root=ET.fromstring(raw);ns={'c':'urn:oasis:names:tc:emergency:cap:1.2'}
    def value(name,node=root):return node.findtext('c:'+name,default='',namespaces=ns)
    if root.tag!='{urn:oasis:names:tc:emergency:cap:1.2}alert':raise SourceError('Unsupported CAP namespace/root')
    identifier=value('identifier');sent=value('sent');status=value('status');msg=value('msgType')
    if not identifier or not sent or msg not in ['Alert','Update','Cancel','Ack','Error']:raise SourceError('Invalid CAP identity/lifecycle')
    if parsed(sent)>now+timedelta(minutes=10):raise SourceError('Future CAP sent time')
    infos=[]
    for info in root.findall('c:info',ns):
        effective=value('effective',info) or sent;expires=value('expires',info)
        active=status=='Actual' and msg in ['Alert','Update'] and bool(expires) and parsed(effective)<=now<parsed(expires)
        areas=[{'description':value('areaDesc',a),'polygons':[e.text for e in a.findall('c:polygon',ns)],'circles':[e.text for e in a.findall('c:circle',ns)],'geocodes':[{c.tag.split('}')[-1]:c.text for c in g} for g in a.findall('c:geocode',ns)]} for a in info.findall('c:area',ns)]
        infos.append({'language':value('language',info) or 'en-US','event':value('event',info),'headline':value('headline',info),'description':value('description',info),'instruction':value('instruction',info),'severity':value('severity',info),'urgency':value('urgency',info),'certainty':value('certainty',info),'effective':effective,'expires':expires or None,'active_by_time_and_status':active,'areas':areas})
    return {'identifier':identifier,'sender':value('sender'),'sent':sent,'status':status,'msg_type':msg,'scope':value('scope'),'references':value('references'),'info':infos,'provenance':meta,'geographic_applicability':'Not established by time/status alone.'}
