import pathlib
p = pathlib.Path('tests/test_now_view.py')
t = p.read_text()
old_start = t.index("    def test_the_summary_names_the_nearest_and_the_freshest_station(self):")
old_end = t.index("    def test_the_summary_says_what_is_not_connected(self):")
new = ("    def test_the_summary_leads_with_the_freshest_station_and_names_the_nearest(self):\n" +
       "        # Measured live: a stale AWS row 29 km away led the answer while the fresh METAR\n" +
       "        # 40 km away was mentioned second, so a reader saw a six-month-old temperature first.\n" +
       "        summary = self.compose()['summary']\n" +
       "        self.assertIn('Freshest station report here: AHMEDABAD', summary)\n" +
       "        self.assertIn('reported 2026-09-15T05:30:00+00:00, 60.0 minutes before retrieval', summary)\n" +
       "        self.assertIn('The nearest station (AHMEDABAD at 4.2 km) reported 390.0 minutes before retrieval, so the fresher report leads', summary)\n" +
       "        self.assertLess(summary.index('Freshest station report'), summary.index('The nearest station'), 'the fresh report leads the sentence')\n\n")
t = t[:old_start] + new + t[old_end:]
p.write_text(t)
print('patched test')