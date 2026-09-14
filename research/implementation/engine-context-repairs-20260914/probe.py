"""Bounded live probes for the Phase 1 engine repairs. Records raw responses."""
import json,re,sys,time,urllib.request
OUT=sys.argv[1]
ORIGIN='http://127.0.0.1:8765'
with urllib.request.urlopen(ORIGIN+'/',timeout=10) as page:
    TOKEN=re.search(r'workspace-token" content="([^"]+)"',page.read().decode())[1]

def ask(question,cid=None):
    body={'question':question}
    if cid:body['conversation_id']=cid
    began=time.monotonic()
    request=urllib.request.Request(ORIGIN+'/api/chat',json.dumps(body).encode(),
                                   {'Content-Type':'application/json','Origin':ORIGIN,'X-WeatherGPT-Token':TOKEN})
    try:
        with urllib.request.urlopen(request,timeout=300) as response:packet=json.load(response)
    except urllib.error.HTTPError as exc:packet={'error':exc.read().decode()[:800],'status':'http_error'}
    packet['_seconds']=round(time.monotonic()-began,2)
    print(f"[{packet.get('status')}] {packet['_seconds']}s :: {question[:70]}")
    return packet

runs={}
# A01: an explicitly named new measure inside a continuation.
a=ask('What is the chance of rain in Kochi, Kerala tomorrow afternoon, with gusts and the feels like temperature?')
runs['a01-1']=a
cid=a.get('conversation_id')
b=ask('Compare the rain amount for that same afternoon period with GFS too',cid)
runs['a01-2']=b
# A02: an explicitly Gujarati request.
g=ask('રાજકોટમાં કાલે સવારે વરસાદની સંભાવના કેટલી છે?')
runs['a02-1']=g
# A03: retrieval task followed by an explanation of it in one request.
e=ask('Give me the latest METAR for VOBL and explain what it means')
runs['a03-1']=e
json.dump(runs,open(OUT,'w'),ensure_ascii=False,indent=1)
print('saved',OUT)
