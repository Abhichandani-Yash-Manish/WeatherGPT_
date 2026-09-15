import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()
anchor = '## Status and open work'
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, "## What it feels like to use\n\nOpen the workspace, and it shows the working place, the published district warning days, and a composer asking\n*What is it like right now in Ahmedabad?*. Answering that leads with the freshest station report (name,\ndistance, age), then the published district day with its issue instant and source, then the next six model\nhours, then one line naming what is not connected. Follow up in the same conversation with *and what about the\nafternoon?* and only the window changes. Ask *Is any warning in force for Patna, Bihar today?* and the answer's\nactions offer **Write the alert brief** and **Save to briefcase**; ask about a district agromet advisory and\nthey offer **Write the advisory brief**; any answer with a point offers **Right now here** and **Write a\nbriefing**, which writes a dated briefing into the local series. Every answer also shows *What was retrieved,\nand what is missing*: the pending questions, the search counts, the editions read with their printed issue dates\nand currency, and the source of every value. [docs/63](docs/63-product-walkthrough.md) walks the thirteen\nrecorded journeys, with what is fast and what is still slow." + chr(10) + chr(10) + anchor, 1)
doc_anchor = '- [The chat surface and the key you paste](docs/62-chat-surface-and-provider-ux.md)'
assert t.count(doc_anchor) == 1, 'docs link anchor'
t = t.replace(doc_anchor, "- [The product, walked through](docs/63-product-walkthrough.md) - thirteen recorded journeys with what a user gets in five minutes, the rebuilt first-run screen, and the honest list of what is still slow or unconnected." + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['product_review_batch'] = {
    'report': 'docs/63-product-walkthrough.md',
    'evidence_directory': 'research/implementation/product-review-20260915',
    'operational_ready': False,
    'scope': "A product review of the whole workspace: thirteen live journeys re-run and recorded (eleven answered, one honest partial asking for a growth stage, one honest not-connected for tide), the first-run screen rebuilt around the build's strongest journeys with the composer asking the right-now question, welcome text that names what is not connected and how a cloud key is added, and the walkthrough document with the journey table and the cold-start latency limit.",
    'automated_tests': 860,
    'javascript_component_checks': 70,
    'measured': {'journeys': 13, 'answered': 11, 'partial': 1, 'unavailable': 1,
                 'fastest_seconds': 0.0, 'slowest_seconds': 146.2,
                 'cold_paths': {'right_now_stations': 146.2, 'district_warning': 67.0},
                 'same_window_across_scripts': True,
                 'shared_name_place_decided_by': 'the connected product, disclosed'},
    'limitations': ['Cold first reads of the station and warning layers take 67-146 seconds on this machine.',
                    'Corpus coverage is uneven by family: 571 district agromet, five state editions, one edition per national product.',
                    'Radar and satellite imagery, sea-area and coastal bulletins, flood extent and delivery remain unconnected.',
                    'No native-speaker review; no mobile or screen-reader acceptance; no valid OpenRouter key call yet.']}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/63-product-walkthrough.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R33 is recorded'):
        glines.insert(index + 1, "- **R34 is recorded in [docs/63](63-product-walkthrough.md).** The workspace was reviewed as a product: thirteen live journeys recorded, eleven answered, one an honest partial (a growth stage is needed) and one an honest not-connected (tide has no product). The first-run screen now leads with what the build does best - right now, today's published warning, the farm advisory, a trend, an airport report - the composer asks the right-now question, and the welcome names radar, satellite imagery, sea-area and coastal bulletins, flood extent and delivery as not connected, plus where a cloud key goes. **R34 closes no gap-register item and settles no claim**: cold reads of the station and warning layers take 67-146 seconds on this machine, the corpus is uneven by family, four PS-feature parts remain unconnected, and no native speaker has reviewed the rendered languages.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'What it feels like to use' in r.read_text(), '| batch', 'product_review_batch' in h.read_text(), '| R34', inserted)