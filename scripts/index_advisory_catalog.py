"""Index the publisher's advertised nationwide district directory, not every PDF."""
import concurrent.futures,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from weathergpt_data.foundation import Foundation
from weathergpt_data.advisories import catalog
from weathergpt_data.transport import write_json,utcnow,stamp
ROOT=Path(__file__).resolve().parents[1]
def main():
 f=Foundation();states=catalog(f.store);out=ROOT/'data/processed/foundation';results=[]
 def check(s):
  try:return {'state':s['id'],**catalog(f.store,s['id'])}
  except Exception as exc:return {'state':s['id'],'status':'error','error':str(exc)}
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  results=list(pool.map(check,states['records']))
 summary={'indexed_at_utc':stamp(utcnow()),'source_id':'S57','states':states,'results':results,'listed_regions':len(results),'listed_district_entries':sum(r.get('count',0) for r in results),'errors':[r for r in results if r['status']=='error'],'limitations':['Publisher directory, not a validated current LGD inventory.','Listing does not prove bulletin freshness or successful PDF extraction for every entry.']}
 write_json(out/'advisory-directory.json',summary)
 print({k:summary[k] for k in ['listed_regions','listed_district_entries','errors']})
if __name__=='__main__':main()
