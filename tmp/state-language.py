import pathlib
p = pathlib.Path('weathergpt_data/document_ingest.py')
t = p.read_text()
start = t.index('def ingest_state(')
old = "    record.update(issue_date=info['issue_date'], issue_date_basis=info['issue_date_basis'],"
at = t.index(old, start)
insert = ("    # A state edition can be published in the state's language: the sampled Rajasthan and Uttar" + chr(10) +
          "    # Pradesh editions are in Devanagari. The language is measured from the front page and" + chr(10) +
          "    # recorded with its basis, rather than inherited from the family default." + chr(10) +
          "    front = ((pages[0].get('text') if isinstance(pages[0], dict) else str(pages[0])) or '')" + chr(10) +
          "    devanagari = len(re.findall('[\\u0900-\\u097f]', front))" + chr(10) +
          "    if devanagari > 40 and devanagari > len(re.findall('[A-Za-z]', front)):" + chr(10) +
          "        info['language'] = 'hi'" + chr(10) +
          "        info['language_basis'] = 'detected from the front page script'" + chr(10) +
          "    else:" + chr(10) +
          "        info['language_basis'] = 'the family default'" + chr(10))
t = t[:at] + insert + t[at:]
p.write_text(t)
print('patched language detection')