import json, re, urllib.request, pathlib, sys
sys.path.insert(0, str(pathlib.Path('.').resolve()))
SLUGS = ['mumbai','pune','jaipur','lucknow','bhopal','chennai','bengaluru','hyderabad','kolkata','bhubaneswar','patna','ranchi','raipur','chandigarh','dehradun','shimla','guwahati','nagpur','aurangabad','vijayawada','thiruvananthapuram','panaji','ahmedabad']
URL = 'https://mausam.imd.gov.in/%s/mcdata/agromet.pdf'
results = []
for slug in SLUGS:
    url = URL % slug
    row = {'slug': slug, 'url': url}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'WeatherGPT-local-prototype/0.1'})
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read(4_000_000)
            row['status'] = response.status
            row['bytes'] = len(body)
            row['content_type'] = response.headers.get('Content-Type')
        row['is_pdf'] = body[:4] == b'%PDF'
        text_ok = b'agromet advisory service bulletin' in body.lower()
        row['marker_agromet_bulletin'] = text_ok
        row['issued_on'] = bool(re.search(rb'Issued on\s*:?\s*\d{2}-\d{2}-\d{4}', body, re.I))
    except Exception as failure:
        row['status'] = 'error'
        row['why'] = type(failure).__name__ + ': ' + str(failure)[:120]
    results.append(row)
    print('%-22s %-6s %-9s pdf=%s marker=%s' % (slug, str(row.get('status'))[:6], str(row.get('bytes') or '-'), row.get('is_pdf'), row.get('marker_agromet_bulletin')))
pathlib.Path('research/discovery').mkdir(parents=True, exist_ok=True)
pathlib.Path('tmp/state-agromet-probe.json').write_text(json.dumps(results, indent=2))
print('verified:', [r['slug'] for r in results if r.get('marker_agromet_bulletin')])