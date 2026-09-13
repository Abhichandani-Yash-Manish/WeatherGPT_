"""Explicit bounded numeric ingestion; never installs a recurring scheduler."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from weathergpt_data.ingestion import IngestionDB,run_batch,backup,restore


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',default='data/runtime/ingestion/ingestion.sqlite')
    p.add_argument('--raw-root',default='data/runtime/ingestion/raw')
    s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('enqueue');q.add_argument('--product',required=True,choices=['forecast','marine','river'])
    q.add_argument('--lat',required=True,type=float);q.add_argument('--lon',required=True,type=float)
    q.add_argument('--days',default=3,type=int);q.add_argument('--cycle-at',required=True)
    q=s.add_parser('run');q.add_argument('--max-jobs',type=int,default=10)
    s.add_parser('status')
    q=s.add_parser('latest');q.add_argument('--stream',required=True)
    q=s.add_parser('backup');q.add_argument('--output',required=True)
    q=s.add_parser('restore');q.add_argument('--bundle',required=True);q.add_argument('--output',required=True)
    a=p.parse_args();db=None
    try:
        if a.command=='restore':result=restore(a.bundle,a.output)
        else:
            db=IngestionDB(a.database)
            if a.command=='enqueue':
                jid=db.enqueue(a.product,a.lat,a.lon,a.days,a.cycle_at)
                result=dict(db.db.execute('SELECT id,stream,state FROM jobs WHERE id=?',(jid,)).fetchone())
            elif a.command=='run':result=run_batch(db,a.raw_root,a.max_jobs)
            elif a.command=='status':result=db.status()
            elif a.command=='latest':result=db.latest(a.stream)
            elif a.command=='backup':result=backup(db,a.raw_root,a.output)
        print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
    finally:
        if db:db.close()


if __name__=='__main__':main()
