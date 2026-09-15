import pathlib
p = pathlib.Path('weathergpt_data/document_ingest.py')
t = p.read_text()
old_field = "        markers=['agromet advisory service bulletin'],"
assert t.count(old_field) == 1, t.count(old_field)
new_field = ("        # Sampled real front pages, 15 September 2026: the Ahmedabad (Gujarat) edition is English and" + chr(10) +
             "        # says 'agromet advisory service bulletin'; the Jaipur (Rajasthan) and Lucknow (Uttar Pradesh)" + chr(10) +
             "        # editions are Hindi and say 'संयुक्त कृषि-मौसम सलाहकार सेवा बुलेटिन', which extraction renders" + chr(10) +
             "        # with spacing artefacts around the conjuncts. A marker list fitted to one failure is not" + chr(10) +
             "        # evidence: these two markers come from the two sampled Hindi editions, and other centres'" + chr(10) +
             "        # layouts stay unreviewed until a real front page is sampled for them." + chr(10) +
             "        markers=['agromet advisory service bulletin', 'मौसम सलाहकार', 'संयुक्त क'],")
t = t.replace(old_field, new_field, 1)
old_issuer = "        issuer=['india meteorological department', 'amfu', 'damu', 'agricultural university'],"
assert t.count(old_issuer) == 1, t.count(old_issuer)
new_issuer = ("        issuer=['india meteorological department', 'amfu', 'damu', 'agricultural university'," + chr(10) +
              "                'भारत मौसम विज्ञान विभाग', 'मौसम विज्ञान विभाग', 'मौसम विज्ञान केन्द्र', 'कृषि'],")
t = t.replace(old_issuer, new_issuer, 1)
old_date = "        issue_date=[('printed', r'Issued on\\s*:?\\s*(\\d{2}-\\d{2}-\\d{4})')],"
assert t.count(old_date) == 1, t.count(old_date)
new_date = ("        issue_date=[('printed', r'Issued on\\s*:?\\s*(\\d{2}-\\d{2}-\\d{4})')," + chr(10) +
            "                    ('printed_dotted_local', r'जारी\\s*तिथि\\s*:?\\s*(\\d{2}\\.\\d{2}\\.\\d{4})')," + chr(10) +
            "                    ('printed_dmy_local', r'जारी\\s*तिथि\\s*:?\\s*(\\d{2}-\\d{2}-\\d{4})')],")
t = t.replace(old_date, new_date, 1)
old_number = "        times=[('bulletin_number', r'Bulletin No\\.\\s*([\\d/]+)')]),"
assert t.count(old_number) == 1, t.count(old_number)
new_number = ("        times=[('bulletin_number', r'Bulletin No\\.\\s*([\\d/]+)')," + chr(10) +
              "               ('bulletin_number_local', r'बुलेटिन संख्या\\s*:?\\s*([\\d/]+)')]),")
t = t.replace(old_number, new_number, 1)
p.write_text(t)
print('patched family spec')