"""Representative nationwide live smoke check; bounded samples, no operational alerting."""
import concurrent.futures,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from weathergpt_data.foundation import Foundation
from weathergpt_data.transport import utcnow,stamp,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
    f=Foundation();out=ROOT/'data/processed/foundation'/utcnow().strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True)
    jobs={}
    for name,lat,lon in [('ahmedabad',23.02579,72.58727),('delhi',28.6139,77.209),('mumbai',19.076,72.8777),('chennai',13.0827,80.2707),('guwahati',26.1445,91.7362),('srinagar',34.0837,74.7973)]:
        jobs['forecast-'+name]=(lambda lat=lat,lon=lon:f.forecast(lat,lon))
    for name,lat,lon in [('arabian-sea',20,69),('bay-of-bengal',15,85),('andaman-sea',10,93)]:jobs['marine-'+name]=(lambda lat=lat,lon=lon:f.marine(lat,lon))
    ids=['VAAH','VIDP','VABB','VOMM','VECC','VEGT']
    for kind in ['metar','taf','stationinfo']:jobs['aviation-'+kind]=(lambda kind=kind:f.aviation(ids,kind))
    jobs.update({'national-warning-snapshot':lambda:f.warning_snapshot(),'cap-messages':lambda:f.cap(),'history-ahmedabad':lambda:f.history(23.02579,72.58727,'2025-07-01','2025-07-07'),'river-ahmedabad':lambda:f.river(23.02579,72.58727),'place-ahmedabad':lambda:f.places('Ahmedabad')})
    def run(name,fn):
        try:
            result=fn();write_json(out/(name+'.json'),result)
            summary={'name':name,'status':result['status'],'records':result['count'],'source_id':result['source_id'],'coverage':result.get('coverage',{}),'provenance':result['provenance']}
        except Exception as exc:summary={'name':name,'status':'error','error_type':type(exc).__name__,'error':str(exc)}
        print(name,summary['status'],summary.get('records'),flush=True)
        return summary
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(run,name,fn) for name,fn in jobs.items()];results=[p.result() for p in futures]
    write_json(out/'smoke-report.json',{'checked_at_utc':stamp(utcnow()),'scope':'Representative locations, not exhaustive Indian territory/station coverage; reference_only is not an operational warning pass.','results':results})
    write_json(ROOT/'data/processed/foundation/latest.json',{'directory':str(out.relative_to(ROOT))})
    print('REPORT',out/'smoke-report.json',flush=True)
if __name__=='__main__':main()
