import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()

old_rain = r"(rain|rainfall|precipitation|shower|barish|baarish|varsha|barsat|paani)"
assert t.count(old_rain) == 1, ('rain', t.count(old_rain))
new_rain = r"(rain|rainfall|precipitation|shower|barish|baarish|varsha|barsat|paani|बारिश|वर्षा|વરસાદ|மழை|వర్షం|ಮಳೆ|മഴ|বৃষ্টি|ବର୍ଷା|ਮੀਂਹ)"
t = t.replace(old_rain, new_rain, 1)

old_temp = r"(temperature|temp|hot|cold|warm|cool|tapman|garmi|thand)"
assert t.count(old_temp) == 1, ('temp', t.count(old_temp))
new_temp = r"(temperature|temp|hot|cold|warm|cool|tapman|garmi|thand|तापमान|તાપમાન|வெப்பநிலை|ఉష్ణోగ్రత|ತಾಪಮಾನ|താപനില|তাপমাত্রা|ତାପମାତ୍ରା|ਤਾਪਮਾਨ)"
t = t.replace(old_temp, new_temp, 1)

old_hum = r"(humidity|humid|moisture)"
assert t.count(old_hum) == 1, ('hum', t.count(old_hum))
new_hum = r"(humidity|humid|moisture|नमी|ભેજ|ஈரப்பதம்|తేమ|ಆರ್ದ್ರತೆ|আর্দ্রতা|ଆର୍ଦ୍ରତା)"
t = t.replace(old_hum, new_hum, 1)

old_wind = r"(wind|windy|breeze|havaman)"
assert t.count(old_wind) == 1, ('wind', t.count(old_wind))
new_wind = r"(wind|windy|breeze|havaman|हवा|પવન|காற்று|గాలి|ಗಾಳಿ|കാറ്റ്|বাতাস|ପବନ|ਹਵਾ)"
t = t.replace(old_wind, new_wind, 1)
p.write_text(t)
print('patched vocabulary')