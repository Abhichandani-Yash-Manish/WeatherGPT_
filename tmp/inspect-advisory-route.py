import json, re, urllib.request
BASE='http://127.0.0.1:8790'
page=urllib.request.urlopen(BASE+'/',timeout=30).read().decode()
token=re.search(r'name="workspace-token" content="([^"]+)"',page).group(1)
req=urllib.request.Request(BASE+'/api/advisories/brief?region=Ahmedabad&crop=cotton&topic=general&mode=source_lookup&day=1')
req.add_header('X-WeatherGPT-Token',token); req.add_header('Host','127.0.0.1:8790')
d=json.loads(urllib.request.urlopen(req,timeout=120).read().decode())
print('status:', d.get('status'))
print('keys:', sorted(d.keys()))
print('why:', d.get('why'))
print('notes:', (d.get('notes') or [])[:2])
advice=d.get('published_advice') or {}
print('passages:', len(advice.get('passages') or []), '| family:', advice.get('family'), '| region:', advice.get('region'))