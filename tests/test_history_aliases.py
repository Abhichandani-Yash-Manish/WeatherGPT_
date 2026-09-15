"""Historical alias candidates: source-lined options, never an unasked substitution.

The publisher's historical tables keep their own district spellings (Mysore, Orissa).
When a name misses, the place index can offer candidates, but the rule this pins is
that a candidate is used only after the user chooses it and is labelled as a
place-index label rather than a reviewed crosswalk.
"""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from weathergpt_data.dialogue import apply_historical_choice
from weathergpt_data.research_answers import _same_series_state, alias_candidates


class StubGazetteer:
    def __init__(self, matches, alternates=None):
        self.matches = matches
        self.alternates_map = alternates or {}

    def search(self, name, state='', district=''):
        if isinstance(self.matches, dict):
            return self.matches.get(name, [])
        return self.matches

    def alternates(self, place_id, limit=200):
        return self.alternates_map.get(place_id, [])


def database(directory, series):
    path = Path(directory) / 'districts.sqlite'
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE rainfall (state TEXT,district TEXT,year INTEGER,value TEXT)')
    con.executemany('INSERT INTO rainfall VALUES (?,?,?,?)', [(state, district, 2010, '100.0') for state, district in series])
    con.commit()
    con.close()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (Path(directory) / 'build-manifest.json').write_text(json.dumps({'outputs': {path.name: digest}}))
    return path


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_place_alternate_name_can_be_offered_when_the_series_uses_it(self):
        gazetteer = StubGazetteer([{'id': '1', 'name': 'Mysuru', 'admin1': 'Karnataka', 'admin2': 'Mysuru'}],
                                  {'1': ['Mysore', 'Maisuru']})
        db = database(self.tmp.name, [('Karnataka', 'Mysore')])
        candidates = alias_candidates({'name': 'Mysuru', 'state': 'Karnataka'}, db, gazetteer=gazetteer)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['selection_id'], 'history-district:Karnataka|Mysore')
        self.assertEqual(candidates[0]['historical_district'], {'name': 'Mysore', 'state': 'Karnataka'})
        self.assertIn('another name', candidates[0]['label'])
        self.assertNotIn('substitut', candidates[0]['label'])

    def test_a_city_can_be_offered_its_district_series(self):
        gazetteer = StubGazetteer([{'id': '2', 'name': 'Bhubaneswar', 'admin1': 'Odisha', 'admin2': 'Khordha'}])
        db = database(self.tmp.name, [('Orissa', 'Khordha')])
        candidates = alias_candidates({'name': 'Bhubaneswar', 'state': 'Odisha'}, db, gazetteer=gazetteer)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['historical_district']['name'], 'Khordha')
        self.assertIn('places Bhubaneswar in Khordha district', candidates[0]['label'])
        self.assertTrue(_same_series_state('Orissa', 'Odisha'))

    def test_an_older_district_spelling_from_the_district_place_is_offered(self):
        gazetteer = StubGazetteer(
            {'Bhubaneswar': [{'id': '2', 'name': 'Bhubaneswar', 'admin1': 'State of Odisha', 'admin2': 'Khordha'}],
             'Khordha': [{'id': '3', 'name': 'Khordha', 'admin1': 'State of Odisha', 'admin2': 'Khordha'}]},
            {'2': [], '3': ['Khurda', 'Khurdha']})
        db = database(self.tmp.name, [('Orissa', 'Khurda')])
        candidates = alias_candidates({'name': 'Bhubaneswar', 'state': 'Odisha'}, db, gazetteer=gazetteer)
        self.assertEqual([c['historical_district']['name'] for c in candidates], ['Khurda'])
        self.assertIn("another name for Khordha", candidates[0]['label'])

    def test_a_name_with_no_candidate_offers_nothing(self):
        gazetteer = StubGazetteer([])
        db = database(self.tmp.name, [('Karnataka', 'Mysore')])
        self.assertEqual(alias_candidates({'name': 'Nowhere', 'state': ''}, db, gazetteer=gazetteer), [])

    def test_candidates_are_capped_and_not_duplicated(self):
        gazetteer = StubGazetteer([{'id': '1', 'name': 'X', 'admin1': 'Karnataka', 'admin2': 'Mysore'}],
                                  {'1': ['Mysore', 'MYSORE', 'Mysuru', 'Maisuru']})
        db = database(self.tmp.name, [('Karnataka', 'Mysore'), ('Karnataka', 'Maisuru')])
        candidates = alias_candidates({'name': 'X', 'state': 'Karnataka'}, db, gazetteer=gazetteer)
        self.assertLessEqual(len(candidates), 3)
        self.assertEqual(len({c['selection_id'] for c in candidates}), len(candidates))

    def test_the_confirmed_choice_rewrites_only_the_place(self):
        plan = {'tasks': [{'kind': 'history', 'operation': 'lookup', 'place_indices': [0]}],
                'places': [{'name': 'Mysuru', 'state': 'Karnataka', 'district': '', 'kind': 'settlement'}],
                'clarification': ''}
        selected = {'historical_district': {'name': 'Mysore', 'state': 'Karnataka'}, 'for_place_name': 'Mysuru'}
        rewritten = apply_historical_choice(plan, selected)
        self.assertEqual(rewritten['places'][0]['name'], 'Mysore')
        self.assertEqual(rewritten['places'][0]['kind'], 'district')
        self.assertEqual(rewritten['changed_fields'], ['places'])
        self.assertEqual(rewritten['tasks'][0]['operation'], 'lookup')


if __name__ == '__main__':
    unittest.main()
