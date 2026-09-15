import pathlib
p = pathlib.Path('tests/test_state_agromet_sweep.py')
t = p.read_text()
old = "        record = self.run_one(minimal_pdf(ENGLISH_FRONT.encode('utf-8')))"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, "        record = self.run_one(minimal_pdf(ENGLISH_FRONT.encode('utf-8')), state='Gujarat')", 1)
old2 = "        self.assertGreaterEqual(len(measured), 1)"
assert t.count(old2) == 1
t = t.replace(old2, "        self.assertGreaterEqual(len(measured), 5, 'the five ingested states carry their name check')", 1)
anchor = "if __name__ == '__main__':"
assert t.count(anchor) == 1
t = t.replace(anchor, "\n\nclass DevanagariMarkerTests(unittest.TestCase):\n    def marker(self, text):\n        from weathergpt_data.document_ingest import family, marker_match\n        return marker_match([{'text': text}], family('state_agromet'))\n\n    def test_the_two_sampled_hindi_front_pages_are_recognised(self):\n        self.assertIn('मौसम सलाहकार', self.marker(HINDI_FRONT))\n        lucknow = ('Govt. of India/भारत सरकार Ministry of Earth Sciences/पृथ्वी विज्ञान मंत्रालय '\n                   'India Meteorological Department/भारत मौसम विज्ञान विभाग Regional Meteorological Centre Lucknow/ '\n                   'प्रादेशिक मौसम केन्द्र, लखनऊ उत्तर प्रदेश संयुक्त कृषि-मौसम सलाहकार सेवा बुलेटिन')\n        self.assertIn('मौसम सलाहकार', self.marker(lucknow))\n\n    def test_an_unrelated_bulletin_is_refused_rather_than_matched_by_an_empty_pattern(self):\n        from weathergpt_data.transport import SourceError\n        with self.assertRaises(SourceError):\n            self.marker('Some other bulletin about rainfall and temperature in Teststate')\n\n    def test_squashing_a_devanagari_title_does_not_produce_an_empty_pattern(self):\n        from weathergpt_data.document_ingest import _squash\n        self.assertTrue(_squash('मौसम सलाहकार'))\n        self.assertNotIn(_squash('मौसम सलाहकार'), _squash('Some other bulletin'))\n" + chr(10) + anchor, 1)
p.write_text(t)
print('patched tests')
