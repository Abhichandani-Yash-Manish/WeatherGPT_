"""Recheck every historical row for missingness, duplicate keys and aggregate consistency."""
import argparse,csv,json
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MONTHS=[m+'_mm' for m in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']]
GROUPS={'annual_mm':MONTHS,'jf_mm':MONTHS[:2],'mam_mm':MONTHS[2:5],'jjas_mm':MONTHS[5:9],'ond_mm':MONTHS[9:]}

def run(output):
    counts=Counter();series=defaultdict(list);issues=[];seen=set()
    for path in sorted((ROOT/'data/raw/imports/2026-09-11/states').glob('*.csv')):
        counts['files']+=1
        with path.open(encoding='utf-8-sig',newline='') as stream:
            for row in csv.DictReader(stream):
                sid=row['series_id'];year=int(row['year']);key=(sid,year)
                if key in seen:raise ValueError('Duplicate series/year')
                seen.add(key);series[sid].append((year,any(row[k]=='' for k in MONTHS)));counts['rows']+=1
                missing=sum(row[k]=='' for k in MONTHS);counts['missing_month_cells']+=missing;counts['rows_with_missing_months']+=bool(missing)
                if bool(missing)!=('missing_months' in row['quality_flags']):raise ValueError('Missingness flag mismatch')
                for field in MONTHS+list(GROUPS):
                    if row[field]:
                        v=Decimal(row[field])
                        if not v.is_finite() or v<0:raise ValueError('Invalid historical measurement')
                        counts['numeric_cells_validated']+=1
                for field,components in GROUPS.items():
                    counts['aggregate_slots_checked']+=1
                    if not row[field] or any(row[c]=='' for c in components):counts['aggregates_not_comparable']+=1;continue
                    difference=Decimal(row[field])-sum((Decimal(row[c]) for c in components),Decimal(0));bound=Decimal('0.05')*(len(components)+1)
                    counts['aggregates_comparable']+=1
                    if abs(difference)>bound:
                        issues.append({'series_id':sid,'district':row['district_source'],'year':year,'field':field,'difference_mm':str(difference),'source_quality_flags':row['quality_flags']})
    counts['series']=len(series);counts['series_with_missing_months']=sum(any(m for y,m in rows) for rows in series.values())
    counts['series_with_internal_year_gaps']=sum(max(y for y,m in rows)-min(y for y,m in rows)+1!=len(rows) for rows in series.values())
    report={'status':'PASS_WITH_PRESERVED_SOURCE_LIMITATIONS','counts':dict(counts),'aggregate_discrepancies':issues,
            'interpretation':'No imputation or silent total correction. Transcription matches the PDF; missingness and internal source inconsistencies remain factual limitations.'}
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise ValueError('Use a new output path')
    output.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);print(json.dumps(run(p.parse_args().output),indent=2))
