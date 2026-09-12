import argparse,json,sys,sqlite3
from pathlib import Path
from .climate import build,lookup

def main():
    parser=argparse.ArgumentParser(description='WeatherGPT data foundation: deterministic local queries and sourced public data')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('build-climate')
    q=sub.add_parser('lookup-climate');q.add_argument('--database',required=True);q.add_argument('--source',required=True,choices=['S25','S26']);q.add_argument('--year',required=True,type=int);q.add_argument('--period',default='ANNUAL');q.add_argument('--geography',default='all-india')
    sub.add_parser('build-districts')
    q=sub.add_parser('district-history');q.add_argument('--database',required=True);q.add_argument('--state',required=True);q.add_argument('--district',required=True);q.add_argument('--year',required=True,type=int);q.add_argument('--period',default='annual')
    for name in ['forecast','marine','history','river','warnings']:
        q=sub.add_parser(name);q.add_argument('--lat',type=float,required=name!='warnings');q.add_argument('--lon',type=float,required=name!='warnings');q.add_argument('--output');q.add_argument('--refresh',action='store_true')
        if name in ['forecast','marine','river']:q.add_argument('--days',type=int,default=3 if name!='river' else 7)
        if name=='history':q.add_argument('--start',required=True);q.add_argument('--end',required=True)
    q=sub.add_parser('aviation');q.add_argument('--ids',required=True);q.add_argument('--kind',choices=['metar','taf','stationinfo'],default='metar');q.add_argument('--output');q.add_argument('--refresh',action='store_true')
    q=sub.add_parser('places');q.add_argument('name');q.add_argument('--output')
    q=sub.add_parser('cap');q.add_argument('--output');q.add_argument('--refresh',action='store_true')
    q=sub.add_parser('advisory-catalog');q.add_argument('--language',choices=['en','local'],default='en');q.add_argument('--state');q.add_argument('--output')
    q=sub.add_parser('advisory');q.add_argument('--language',choices=['en','local'],default='en');q.add_argument('--state',required=True);q.add_argument('--district',required=True);q.add_argument('--output')
    q=sub.add_parser('marine-bulletin');q.add_argument('--kind',choices=['sea','coastal'],required=True);q.add_argument('--document-index',type=int);q.add_argument('--output')
    sub.add_parser('readiness')
    args=parser.parse_args()
    try:
        cmd=args.command
        if cmd=='build-climate':result={'directory':str(build())}
        elif cmd=='lookup-climate':result=lookup(args.database,args.source,args.year,args.period,args.geography)
        elif cmd=='build-districts':
            from .districts import build as build_districts
            result={'directory':str(build_districts())}
        elif cmd=='district-history':
            from .districts import lookup as district_lookup
            result=district_lookup(args.database,args.state,args.district,args.year,args.period)
        elif cmd=='readiness':result=json.loads((Path(__file__).resolve().parents[1]/'data/registry/readiness.json').read_text())
        else:
            from .foundation import Foundation
            f=Foundation()
            if cmd in ['forecast','marine','river']:result=getattr(f,cmd)(args.lat,args.lon,args.days,args.refresh)
            elif cmd=='warnings':result=f.warning_snapshot(args.lat,args.lon,args.refresh)
            elif cmd=='history':result=f.history(args.lat,args.lon,args.start,args.end,args.refresh)
            elif cmd=='aviation':result=f.aviation(args.ids.split(','),args.kind,args.refresh)
            elif cmd=='places':result=f.places(args.name)
            elif cmd=='cap':result=f.cap(args.refresh)
            elif cmd=='marine-bulletin':
                from .bulletins import catalog,document
                result=catalog(f.store,args.kind) if args.document_index is None else document(f.store,args.kind,args.document_index)
            elif cmd=='advisory-catalog':
                from .advisories import catalog
                result=catalog(f.store,args.state,args.language)
            elif cmd=='advisory':
                from .advisories import document
                result=document(f.store,args.state,args.district,args.language)
        if getattr(args,'output',None):
            from .transport import write_json
            write_json(args.output,result);print(json.dumps({'output':args.output,'status':result.get('status','ok'),'records':result.get('count')}))
        elif cmd in ['build-climate','build-districts']:print(result['directory'])
        else:print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError) as exc:
        print(json.dumps({'status':'error','message':str(exc),'error_type':type(exc).__name__}),file=sys.stderr);raise SystemExit(2)
if __name__=='__main__':main()
