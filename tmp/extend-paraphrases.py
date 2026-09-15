import pathlib
p = pathlib.Path('scripts/measure_paraphrases.py')
t = p.read_text()
old = "      'Is rain expected for Ahmedabad, Gujarat tomorrow morning?')),"
assert t.count(old) == 1, t.count(old)
new = ("      'Is rain expected for Ahmedabad, Gujarat tomorrow morning?'," + chr(10) +
       "      'Ahmedabad, Gujarat ma kale savere varsad thashe?'," + chr(10) +
       "      'कल अहमदाबाद, गुजरात में सुबह बारिश होगी?')),")
t = t.replace(old, new, 1)
anchor = "    ('crosscheck',"
assert t.count(anchor) == 1, t.count(anchor)
compound = ("    ('compound-rain-and-warning', 'Will it rain in Surat, Gujarat tomorrow morning? Is there any warning for Surat today?'," + chr(10) +
            "     [('forecast', 'lookup'), ('warning', 'lookup')]," + chr(10) +
            "     ('Surat, Gujarat me kal subah barish hogi? Aaj koi warning hai?'," + chr(10) +
            "      'Any warning for Surat today, and will it rain there tomorrow morning?' ))," + chr(10))
t = t.replace(anchor, compound + anchor, 1)
p.write_text(t)
print('patched')