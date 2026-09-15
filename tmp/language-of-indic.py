import pathlib
lang = pathlib.Path('weathergpt_data/language.py')
lines = lang.read_text().splitlines(keepends=True)
target = 15 - 1
assert "'kind':{'type':'string','enum':['settlement','district','state','country','relative','unknown']}" in lines[target], repr(lines[target][:80])
lines[target] = lines[target].replace("['settlement','district','state','country','relative','unknown']", "['settlement','district','state','country','relative','unknown','sea_area']")
lang.write_text(''.join(lines))

t = lang.read_text()
old_valid = "p['kind'] not in ['settlement','district','state','country','relative','unknown']"
assert t.count(old_valid) == 1, t.count(old_valid)
t = t.replace(old_valid, "p['kind'] not in ['settlement','district','state','country','relative','unknown','sea_area']", 1)
lang.write_text(t)

planner = pathlib.Path('weathergpt_data/rule_planner.py')
pt = planner.read_text()
old_lang = """def language_of(question):
    \"\"\"The question's language for the planner field, or None when rules must not guess.\"\"\"
    if INDIC.search(question):
        return None
    if HINGLISH.search(question):
        return 'hi-Latn'
    return 'en'"""
assert pt.count(old_lang) == 1, pt.count(old_lang)
new_lang = """def language_of(question):
    \"\"\"The question's language for the planner field, from the script it is written in.

    Devanagari is Hindi, Gujarati is Gujarati, and any other Indic script is named from the
    language registry's script table. Understanding a question in a language never authorises
    claiming an answer in it: the answer-language gate decides that from the user's own
    selection. Refusing to plan an Indic-script question at all was the earlier behaviour, and
    it left the rules floor unable to answer questions it could read perfectly well.
    \"\"\"
    from .languages import LANGUAGES, SCRIPTS
    text = question or ''
    for code, entry in LANGUAGES.items():
        pattern = SCRIPTS.get(entry.get('script'))
        if pattern and pattern != SCRIPTS['latin'] and re.search('[' + pattern + ']', text):
            return code
    if HINGLISH.search(text):
        return 'hi-Latn'
    return 'en'"""
pt = pt.replace(old_lang, new_lang, 1)
planner.write_text(pt)
print('patched')