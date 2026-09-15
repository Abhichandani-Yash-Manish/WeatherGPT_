import pathlib
p = pathlib.Path('weathergpt_data/document_ingest.py')
t = p.read_text()
old = "    return re.sub(r'[^a-z0-9]+', '', (text or '').lower())"
assert t.count(old) == 1, t.count(old)
new = ("    # Letters and digits in ANY script. The earlier [a-z0-9] version squashed a Devanagari" + chr(10) +
       "    # title to the empty string, and the empty string is a substring of every document, so an" + chr(10) +
       "    # Indian-language marker matched everything instead of matching its own title." + chr(10) +
       "    return re.sub(r'[^\\w]+', '', (text or '').casefold(), flags=re.UNICODE)")
t = t.replace(old, new, 1)

anchor = "def ingest_state(store, index, state, address, now=None, fetch_ttl=0, encoder=None):"
assert t.count(anchor) == 1, t.count(anchor)
mapping = ("# The state name as the sampled editions print it, so a Devanagari document can confirm that" + chr(10) +
           "# it is about the state this registry claims. A state with no entry here records its name check" + chr(10) +
           "# as unmeasured rather than as a pass." + chr(10) +
           "STATE_NAMES_IN_DOCUMENT = {" + chr(10) +
           "    'Gujarat': 'ગુજરાત', 'Rajasthan': 'राजस्थान', 'Uttar Pradesh': 'उत्तर प्रदेश'," + chr(10) +
           "    'Karnataka': 'ಕರ್ನಾಟಕ', 'Chhattisgarh': 'छत्तीसगढ़'," + chr(10) + "}" + chr(10) + chr(10))
t = t.replace(anchor, mapping + anchor, 1)
old_named = "    record['state_named_in_document'] = state.lower() in flat"
assert t.count(old_named) == 1, t.count(old_named)
new_named = ("    local = STATE_NAMES_IN_DOCUMENT.get(state, '')" + chr(10) +
             "    record['state_named_in_document'] = state.lower() in flat or (local and local in flat)")
t = t.replace(old_named, new_named, 1)
p.write_text(t)
print('patched squash and state names')