import pathlib
bi = pathlib.Path('weathergpt_data/bulletin_index.py')
t = bi.read_text()
old = "            topic_words={'irrigation':r'irrigat|water log|waterlog|drain|moisture','sowing':r'sow|seed|nursery|land prepar','pest':r'pest|disease|insect|borer|rot|mite|whitefly|thrip|wilt|caterpillar|jassid|larva|fung','nutrition':r'fertiliz|fertilis|urea|nutrient|nitrogen|phosph|potash|manure','harvest':r'harvest|pick|matur|stor'}"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, "            # Each topic carries the words the editions actually print, in their own scripts: a Devanagari state bulletin says सिंचाई, and an English topic word found nothing in it. Measured on 15 September 2026 against the Rajasthan edition.\n            topic_words={'irrigation':r'irrigat|water log|waterlog|drain|moisture|सिंचाई|सिंचन|ભેજ|સિંચાઈ|নীৰ|ನೀರಾವರಿ|సేద్యం',\n                         'sowing':r'sow|seed|nursery|land prepar|बुवाई|बीज|વાવેતર|વાવણી|ಬಿತ್ತನೆ|విత్తనం|விதைப்பு',\n                         'pest':r'pest|disease|insect|borer|rot|mite|whitefly|thrip|wilt|caterpillar|jassid|larva|fung|कीट|रोग|પીડ|રોગ|ಕೀಟ|ರೋಗ|పురుగు|பூச்சி',\n                         'nutrition':r'fertiliz|fertilis|urea|nutrient|nitrogen|phosph|potash|manure|खाद|उर्वरक|ખાતર|ಗೊಬ್ಬರ|ఎరువు|உரம்',\n                         'harvest':r'harvest|pick|matur|stor|कटाई|ધાન|લણણી|ಕೊಯ್ಲು|కోత|அறுவடை'}", 1)
bi.write_text(t)
rp = pathlib.Path('weathergpt_data/rule_planner.py')
rt = rp.read_text()
oldr = """(re.compile(r'\\b(irrigation|water|irrigate|sinchai)\\b', re.I), 'irrigation')"""
assert rt.count(oldr) == 1, rt.count(oldr)
newr = """(re.compile(r'\\b(irrigation|water|irrigate|sinchai|सिंचाई|સિંચાઈ)\\b', re.I), 'irrigation')"""
rt = rt.replace(oldr, newr, 1)
rp.write_text(rt)
print('patched topic vocabulary')
