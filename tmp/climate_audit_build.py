from pathlib import Path
import json,shutil,io,contextlib
b=Path('research/discovery/evidence/pasted-climate-check')
for k,a in [('rainfall','775fe885-f107-4580-b9dc-d382396c1f42'),('temperature','8cb0283a-fa73-4fc8-b632-e76c134afc1b')]:
 shutil.copyfile(Path('/Users/yashabhichandani/.codex/attachments',a,'pasted-text.txt'),b/(k+'.csv'))
code='''import csv, math, statistics, re, html, json
from pathlib import Path
data_dir = Path("evidence/pasted-climate-check")
results = {}
for kind in ["rainfall", "temperature"]:
    rows = list(csv.DictReader((data_dir / (kind + ".csv")).open()))
    years = [int(r["Year"]) for r in rows]
    measures = list(rows[0])[1:18]
    numeric = [float(r[c]) for r in rows for c in measures]
    raw = (data_dir / (kind + "-selected.html")).read_text()
    cells = [html.unescape(re.sub("<[^>]*>", "", x)).strip()
             for x in re.findall(r"<t[dh]\\b[^>]*>(.*?)</t[dh]>", raw, re.S | re.I)]
    source = {}
    for i, cell in enumerate(cells):
        if re.fullmatch(r"(19|20)\\d{2}", cell) and i + 17 < len(cells):
            try: values = [float(x) for x in cells[i+1:i+18]]
            except ValueError: continue
            source.setdefault(cell, values)
    differences = [r["Year"] for r in rows if source.get(r["Year"]) != [float(r[c]) for c in measures]]
    result = {"rows": len(rows), "columns": len(rows[0]), "year_range": [min(years), max(years)],
              "duplicate_years": len(years)-len(set(years)),
              "missing_years": sorted(set(range(1901,2025))-set(years)),
              "empty_cells": sum(v == "" for r in rows for v in r.values()),
              "nonfinite_values": sum(not math.isfinite(v) for v in numeric),
              "source_comparison_different_years": differences,
              "source_numeric_values_compared": len(rows)*len(measures)}
    if kind == "rainfall":
        months = measures[:12]
        discrepancies = [{"year": int(r["Year"]), "annual_minus_months_mm": round(float(r["Annual"])-sum(float(r[m]) for m in months), 5)} for r in rows]
        result["annual_sum_discrepancies"] = discrepancies
        result["annual_discrepancies_above_0_65mm"] = sum(abs(x["annual_minus_months_mm"]) > 0.65 for x in discrepancies)
        result["2024_month_sum_mm"] = sum(float(rows[-1][m]) for m in months)
        result["2024_annual_mm"] = float(rows[-1]["Annual"])
    else:
        baseline = statistics.mean(float(r["Annual"]) for r in rows if 1991 <= int(r["Year"]) <= 2020)
        result["baseline_1991_2020_mean_c"] = baseline
        result["2024_mean_c"] = float(rows[-1]["Annual"])
        result["2024_anomaly_c"] = result["2024_mean_c"] - baseline
    results[kind] = result
print(json.dumps(results, indent=2))
'''
import os
old=Path.cwd();os.chdir('research/discovery');buf=io.StringIO()
with contextlib.redirect_stdout(buf):exec(code,globals())
os.chdir(old)
(b/'audit-results.json').write_text(buf.getvalue())
nb={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'cells':[{'cell_type':'markdown','id':'scope','metadata':{},'source':['# Supplied national climate tables: scoped audit\n','Run from research/discovery. Input files are unmodified copies of the user attachments. Saved official HTML was retrieved on 11 September 2026 (rainfall form region1=WHI; temperature mean series). This checks numeric transcription and structure, not scientific validity or homogeneity. The rainfall discrepancy is retained, not repaired.']},{'cell_type':'code','id':'checks','metadata':{},'execution_count':1,'source':code.splitlines(True),'outputs':[{'output_type':'stream','name':'stdout','text':buf.getvalue().splitlines(True)}]}]}
Path('research/discovery/national-climate-audit.ipynb').write_text(json.dumps(nb,indent=2))
items=[]
for kind in ['rainfall','temperature']:
 s=results[kind]
 caveat='National aggregates cannot establish Ahmedabad conditions, daily extremes or future forecasts.'
 detail=('2024 monthly rainfall sums to 1204.1 mm versus the published annual 1206.6 mm; the difference is present in the official source. Cause unresolved.' if kind=='rainfall' else '2024 anomaly uses the supplied published annual means and a 1991-2020 baseline; it is not a trend or attribution result.')
 items.append({'id':kind+'-usefulness','title':'National '+kind+' history','queries':[{'id':kind+'-audit','source':{'label':'Supplied table and IMD Data Service Portal','files':[{'label':kind+'.csv'}],'links':[{'label':'IMD '+kind+' series','href':'https://dsp.imdpune.gov.in/home_ogd_'+('rainfall' if kind=='rainfall' else 'temp')+'.php'}],'caveats':[caveat,detail],'evidenceFlow':[{'kind':'validation','title':'Structure and source comparison','detail':'124 unique consecutive years; no empty cells or nonfinite numeric values. All 2108 numeric values match the corresponding saved official table.'}]},'reportingPeriod':'1901–2024','summary':'Monthly, seasonal and annual '+('rainfall in mm.' if kind=='rainfall' else 'mean temperature in degrees Celsius.'),'methods':[{'language':'python','code':code}]}]})
Path('research/discovery/national-climate-sources.json').write_text(json.dumps({'schemaVersion':1,'items':items},indent=2))
print('Saved executed audit notebook; rainfall annual discrepancies beyond rounding bound:',results['rainfall']['annual_discrepancies_above_0_65mm'])
