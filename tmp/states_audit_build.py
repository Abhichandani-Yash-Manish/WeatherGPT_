from pathlib import Path
import json,io,contextlib
code='''from pathlib import Path
import csv, collections, math, json
states_dir = Path.home() / "Downloads" / "states"
files = sorted(states_dir.glob("*.csv"))
rows = [r for f in files for r in csv.DictReader(f.open(encoding="utf-8-sig"))]
months = [m + "_mm" for m in ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]]
keys = collections.Counter((r["series_id"],r["year"]) for r in rows)
ahmedabad = [r for r in rows if r["state_source"] == "Gujarat" and r["district_source"] == "Ahmedabad"]
checks = [("annual_mm",months,.65),("jf_mm",months[:2],.15),("mam_mm",months[2:5],.20),("jjas_mm",months[5:9],.25),("ond_mm",months[9:],.20)]
anomalies = []
for field, components, tolerance in checks:
    for r in rows:
        if all(r[k] for k in [field] + components):
            delta = float(r[field]) - sum(float(r[k]) for k in components)
            if abs(delta) > tolerance + 1e-8:
                anomalies.append({"series_id":r["series_id"], "district":r["district_source"], "year":int(r["year"]), "field":field, "difference_mm":round(delta,4)})
result = {"files":len(files), "rows":len(rows), "series":len(set(r["series_id"] for r in rows)),
          "common_schema":len(set(tuple(r) for r in rows)) == 1,
          "year_range":[min(int(r["year"]) for r in rows),max(int(r["year"]) for r in rows)],
          "duplicate_series_year_keys":sum(v>1 for v in keys.values()),
          "rows_missing_months":sum(any(not r[m] for m in months) for r in rows),
          "missing_month_cells":sum(not r[m] for r in rows for m in months),
          "invalid_numeric_values":sum(not math.isfinite(float(v)) or float(v)<0 for r in rows for k,v in r.items() if k.endswith("_mm") and v),
          "flag_mismatches":sum(("missing_months" in r["quality_flags"]) != any(not r[m] for m in months) for r in rows),
          "rows_with_duplicate_source_pages":sum(bool(r["duplicate_source_pages"]) for r in rows),
          "ahmedabad":{"rows":len(ahmedabad),"years":[min(int(r["year"]) for r in ahmedabad),max(int(r["year"]) for r in ahmedabad)],
                       "missing_months":sum(not r[m] for r in ahmedabad for m in months),
                       "source_pages":sorted(set(r["source_page"] for r in ahmedabad))},
          "aggregate_discrepancies_beyond_rounding_bounds":anomalies}
print(json.dumps(result,indent=2))
'''
buf=io.StringIO()
with contextlib.redirect_stdout(buf):exec(code,globals())
b=Path('research/discovery');(b/'states-folder-audit.json').write_text(buf.getvalue())
nb={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'cells':[{'cell_type':'markdown','id':'scope','metadata':{},'source':['# District rainfall folder: usefulness checks\n','Read-only check of user-supplied files. Source page references are retained but have not been reconciled against the original publication. Rounding bounds assume values rounded independently to nearest 0.1 mm; exceeding the bound flags reconciliation, not an automatic repair. No blanks are converted to zero.']},{'cell_type':'code','id':'profile','metadata':{},'execution_count':1,'source':code.splitlines(True),'outputs':[{'output_type':'stream','name':'stdout','text':buf.getvalue().splitlines(True)}]}]}
(b/'states-folder-audit.ipynb').write_text(json.dumps(nb,indent=2))
payload={'schemaVersion':1,'items':[{'id':'district-rainfall-fit','title':'District rainfall history for WeatherGPT','queries':[{'id':'states-folder-check','source':{'label':'User-supplied states folder','files':[{'label':'32 district-rainfall CSV files'}],'metricDefinitions':[{'label':'Record grain','definition':'Each row represents one source district series and year, with monthly, seasonal and annual rainfall in millimetres.'}],'caveats':['Coverage varies by district; the overall collection ends in 2010.','Source-page pointers do not establish complete transcription accuracy or compatibility with present-day district boundaries.'],'evidenceFlow':[{'kind':'validation','title':'Coverage and keys','detail':'60,568 rows and 640 series; no duplicate series/year keys. Ahmedabad has 110 consecutive years, 1901–2010, with no missing monthly values.'},{'kind':'validation','title':'Missingness and reconciliation','detail':'5,018 rows contain missing months, all marked by missing_months. Kendrapada 1920 annual and Oct–Dec totals each exceed component sums by 12.5 mm; both are flagged in the CSV.'}]},'reportingPeriod':'1901–2010; individual series coverage varies','methods':[{'language':'python','code':code}]}]}]}
(b/'states-folder-sources.json').write_text(json.dumps(payload,indent=2))
print('Saved executed notebook and audit results.')
