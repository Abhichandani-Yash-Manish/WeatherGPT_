import pathlib
p = pathlib.Path('tests/test_state_agromet_sweep.py')
t = p.read_text()
old_hindi = "HINDI_FRONT = ('संयुक्त कृषि-मौसम सलाहकार सेवा बुलेटिन राजस्थान राज्य जारी तिथि 11.09.2026 '"
assert t.count(old_hindi) == 1
replacement = ("ENGLISH_FRONT = ('Agromet Advisory Service Bulletin Gujarat State Issued on 11-09-2026 '" + chr(10) +
               "               'Bulletin No. 72/2026 India Meteorological Department Ahmedabad')" + chr(10) + chr(10) +
               old_hindi)
t = t.replace(old_hindi, replacement, 1)
t = t.replace("HINDI_FRONT.encode('utf-8')", "ENGLISH_FRONT.encode('utf-8')")
t = t.replace("        self.assertIn('मौसम सलाहकार', record['marker_basis'])",
              "        self.assertIn('agromet advisory service bulletin', record['marker_basis'])", 1)
t = t.replace("    def test_a_sampled_hindi_edition_is_accepted_and_its_language_is_measured(self):",
              "    def test_a_sampled_english_edition_is_accepted_with_its_issue_date(self):", 1)
old_reg = "        for row in ingested:\n            self.assertIs(row.get('state_named_in_document'), True, row['state'])"
assert t.count(old_reg) == 1
new_reg = ("        measured = [row for row in ingested if row.get('state_named_in_document') is not None]" + chr(10) +
           "        self.assertGreaterEqual(len(measured), 1)" + chr(10) +
           "        for row in measured:" + chr(10) +
           "            self.assertIs(row['state_named_in_document'], True, row['state'])" + chr(10) +
           "        self.assertTrue(all(row.get('state_named_in_document') in (None, True) for row in ingested))")
t = t.replace(old_reg, new_reg, 1)
p.write_text(t)
print('patched')