"""Reconcile the supplied Ahmedabad series with physical PDF pages 611–613."""
import csv,json,re,hashlib
from decimal import Decimal
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
def main():
    base=ROOT/'research/discovery/evidence/foundation-20260912'
    pdf=base/'imd-110-year-rainfall.pdf';reader=PdfReader(pdf)
    source={};problems=[]
    for page in range(611,614):
        text=reader.pages[page-1].extract_text()
        (base/f'rainfall-p{page}.txt').write_text(text)
        for line in text.splitlines():
            m=re.match(r'^AHMEDABAD\s+(\d{4})\s+(.*)$',line.strip())
            if not m:continue
            # Printed fields have one decimal place; remove PDF layout spacing only.
            body=re.sub(r'\s+','',m.group(2));values=re.findall(r'\d+\.\d',body)
            if len(values)!=17 or ''.join(values)!=body:
                problems.append({'page':page,'year':m[1],'reason':'row extraction not exactly 17 one-decimal values'});continue
            year=int(m[1])
            if year in source:raise ValueError('Duplicate PDF year')
            source[year]={'page':page,'values':values}
    raw=ROOT/'data/raw/imports/2026-09-11/states/gujarat.csv'
    rows=[r for r in csv.DictReader(raw.open(encoding='utf-8-sig')) if r['district_source']=='Ahmedabad']
    columns=[m+'_mm' for m in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec','annual','jf','mam','jjas','ond']]
    differences=[];compared=0
    for row in rows:
        year=int(row['year'])
        if year not in source:continue
        for column,value in zip(columns,source[year]['values']):
            compared+=1
            if Decimal(row[column])!=Decimal(value):differences.append({'year':year,'column':column,'csv':row[column],'pdf':value,'page':source[year]['page']})
    result={'source_id':'S27','source_url':'https://imdpune.gov.in/library/public/e-book110.pdf','pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'csv_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'physical_pages':[611,612,613],'csv_years':len(rows),'pdf_years_parsed':len(source),'numeric_cells_compared':compared,'differences':differences,'extraction_problems':problems,'result':'matched' if compared==1870 and not differences and not problems else 'incomplete_or_mismatch','geography_homogeneity':'not established by transcription comparison','usage_note':'PDF page 3 contains reuse/redistribution restrictions; public redistribution clearance unresolved.'}
    (base/'ahmedabad-reconciliation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
