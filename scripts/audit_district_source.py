"""Read-only, coordinate-based comparison of all imported district cells to the IMD PDF.

Uses independently extracted PDF word positions, including empty table cells.
Ambiguous text/geometry is reported as unresolved, never silently repaired.
"""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
import pdfplumber

ROOT=Path(__file__).resolve().parents[1]
FIELDS=[m+'_mm' for m in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec','annual','jf','mam','jjas','ond']]
HEADERS=['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC','ANNUAL','JF','MAM','JJAS','OND']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    assets={p['path']:p['sha256'] for p in json.loads((ROOT/'data/registry/assets.json').read_text())['files']}
    pdf=ROOT/'research/discovery/evidence/foundation-20260912/imd-110-year-rainfall.pdf'
    inputs={};pages=defaultdict(list);records={}
    for path in [pdf]+sorted((ROOT/'data/raw/imports/2026-09-11/states').glob('*.csv')):
        rel=str(path.relative_to(ROOT));inputs[rel]=sha(path)
        if assets.get(rel)!=inputs[rel]:raise ValueError('Input differs from registered evidence: '+rel)
        if path.suffix!='.csv':continue
        with path.open(encoding='utf-8-sig',newline='') as stream:
            for source_row,row in enumerate(csv.DictReader(stream),2):
                row['_file']=rel;row['_row']=source_row
                pages[int(row['source_page'])].append(row);records[(row['series_id'],int(row['year']))]=row
    dbpath=ROOT/'data/processed/districts/district-v1-c8b978172b77182e/districts.sqlite'
    con=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)
    try:
        count=0
        for sid,year,sourcefile,sourcerow,text in con.execute('SELECT series_id,year,source_file,source_row,payload FROM rainfall'):
            row=records[(sid,year)];payload=json.loads(text)
            if sourcefile!=row['_file'] or sourcerow!=row['_row'] or payload!={k:v for k,v in row.items() if not k.startswith('_')}:
                raise ValueError('Imported CSV/database mismatch')
            count+=1
        if count!=len(records):raise ValueError('Missing database rows')
    finally:con.close()
    counts=Counter();series=defaultdict(Counter);issues=[];header_cache={};states=defaultdict(Counter)
    def words_for(reader,pageno):
        page=reader.pages[pageno-1];words=page.extract_words(x_tolerance=1,y_tolerance=2)
        # A few tightly spaced headings are merged by word extraction. Split only
        # recognized text, using the original glyph boundaries for each column.
        for word in list(words):
            parts={'DECANNUAL':['DEC','ANNUAL'],'APRMAY':['APR','MAY']}.get(word['text'])
            if not parts or word['top']>=100:continue
            chars=sorted((c for c in page.chars if c['text'].strip() and
                          c['x0']>=word['x0']-.1 and c['x1']<=word['x1']+.1 and
                          abs(c['top']-word['top'])<.5),key=lambda c:c['x0'])
            if ''.join(c['text'] for c in chars)!=word['text']:continue
            offset=0
            for part in parts:
                segment=chars[offset:offset+len(part)];offset+=len(part)
                words.append({**word,'text':part,'x0':segment[0]['x0'],'x1':segment[-1]['x1']})
        page.close();return words
    with pdfplumber.open(pdf) as reader,(output/'rows.jsonl').open('w') as stream:
        total_pages=len(reader.pages)
        for index,pageno in enumerate(sorted(pages),1):
            words=words_for(reader,pageno)
            for row in pages[pageno]:
                sid=row['series_id'];basepage=int(sid.split('-P')[1])
                if basepage not in header_cache:
                    header_words=words if basepage==pageno else words_for(reader,basepage)
                    headers={w['text']:w for w in header_words if w['text'] in HEADERS and w['top']<100}
                    header_cache[basepage]=headers
                headers=header_cache[basepage];errors=[];differences=[];cells=None
                if set(headers)!=set(HEADERS):errors.append('Incomplete independent PDF column headers')
                yearwords=[w for w in words if w['text']==row['year'] and w['x0']<headers.get('JAN',{'x0':150})['x0']]
                if len(yearwords)!=1:errors.append('PDF page/year identity not unique')
                if not errors:
                    y=yearwords[0];line=[w for w in words if abs(w['bottom']-y['bottom'])<2]
                    label=''.join(w['text'] for w in sorted(line,key=lambda w:w['x0']) if w['x1']<y['x0']+0.1)
                    expected_label=re.sub(r'\s+','',row['district_table_label'])
                    if label!=expected_label:errors.append('District row label does not match independently extracted label')
                    cells=['']*17
                    for word in line:
                        if word['x0']<=y['x0']+0.1:continue
                        if not re.fullmatch(r'\d+\.\d',word['text']):errors.append('Noncanonical or merged PDF numeric token');continue
                        distances=[abs(word['x1']-headers[h]['x1']) for h in HEADERS]
                        column=min(range(17),key=lambda i:distances[i])
                        # Source numbers are right-aligned to headings; require a narrow positional match.
                        if distances[column]>1.5 or cells[column]:errors.append('Ambiguous PDF column position');continue
                        cells[column]=word['text']
                    if not errors:
                        for field,source_value in zip(FIELDS,cells):
                            native=row[field]
                            if (native=='')!=(source_value=='') or (native and Decimal(native)!=Decimal(source_value)):
                                differences.append({'field':field,'csv':native,'pdf':source_value})
                status='unresolved' if errors else 'mismatch' if differences else 'matched'
                result={'series_id':sid,'year':int(row['year']),'page':pageno,'state':row['state_source'],'district':row['district_source'],
                        'status':status,'issues':sorted(set(errors)),'differences':differences}
                stream.write(json.dumps(result,ensure_ascii=False)+'\n')
                counts[status]+=1;series[sid][status]+=1;states[row['state_source']][status]+=1
                if status=='matched':counts['matched_cells_including_blanks']+=17;counts['matched_nonmissing_cells']+=sum(bool(v) for v in cells)
                if errors or differences:issues.append(result)
            if index%100==0:print(json.dumps({'pages_checked':index,'pages_targeted':len(pages),'rows':sum(counts[k] for k in ['matched','mismatch','unresolved'])}),flush=True)
    summary={'source_pdf_pages':total_pages,'source_pages_checked':len(pages),'district_series':len(series),'csv_database_rows_matched':count,
             'csv_database_measure_cells_matched':count*17,'counts':dict(counts),'series_fully_matched':sum(not (v['unresolved'] or v['mismatch']) for v in series.values()),
             'by_state':{k:dict(v) for k,v in states.items()},'inputs':inputs,'pdfplumber_version':pdfplumber.__version__,
             'method':'PDF coordinate/column and district/year checks, independent of CSV value order. Missing cells are compared explicitly.',
             'limitations':['Transcription agreement does not establish measurement accuracy, modern boundary comparability or reuse rights.','No unclear extraction is promoted to a match.']}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'exceptions.json').write_text(json.dumps(issues,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'inputs','by_state'}},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);audit(p.parse_args().output)
