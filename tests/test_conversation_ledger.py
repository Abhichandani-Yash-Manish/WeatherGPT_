"""The conversation ledger: the place a conversation resolved, and search over its turns.

Two claims are held here, and both are about what the ledger refuses to do. It states the place the engine
resolved and nothing else -- an unanswered conversation about Surat carries no place, however many times Surat
appears in its words. And a search reaches every stored turn, not only the opening question, so a reader
looking for what they asked about Surat finds the conversation where Surat was the follow-up.
"""
import json
import sqlite3
import unittest
from datetime import datetime, timezone
import test_answers as fixture
from weathergpt_data.workspace import Workspace

RESOLVED = {'label': 'Ahmedabad, Gujarat', 'latitude': 23.02, 'longitude': 72.57}
SECOND = {'label': 'Kochi, Kerala', 'coordinates': {'latitude': 9.93, 'longitude': 76.26}}


class LedgerTests(unittest.TestCase):
    # The fixture the workspace tests borrow: a geography, a published forecast and a clock.
    publish = fixture.AnswerTests.publish
    add_place = fixture.AnswerTests.add_place
    ask = fixture.AnswerTests.ask

    def setUp(self):
        fixture.AnswerTests.setUp(self)
        self.app = Workspace(self.root / 'jobs.sqlite', self.root / 'raw', self.root / 'geography.sqlite',
                             clock=lambda: self.now)
        self.store = self.root / 'conversations.sqlite'
        with sqlite3.connect(self.store) as db:
            db.execute('CREATE TABLE conversations (id TEXT PRIMARY KEY, payload TEXT, updated TEXT)')
        self.write('a1', {'history': [{'role': 'user', 'content': 'Will it rain in Ahmedabad tomorrow?'},
                                      {'role': 'assistant', 'content': 'Ahmedabad: 12 mm is forecast for tomorrow.'}],
                          'resolved_points': {'place': RESOLVED}}, '2026-09-19T06:00:00+00:00')
        self.write('a2', {'history': [{'role': 'user', 'content': 'Tell me about the fishing season in Surat.'},
                                      {'role': 'assistant', 'content': 'Surat is a coastal district in Gujarat.'}]},
                   '2026-09-19T05:00:00+00:00')
        self.write('a3', {'history': [{'role': 'user', 'content': 'What is the wave height off Kochi?'},
                                      {'role': 'assistant', 'content': 'A wave model reading was returned.'}],
                          'resolved_points': {'point': SECOND}}, '2026-09-18T09:00:00+00:00')

    def write(self, cid, state, updated):
        with sqlite3.connect(self.store) as db:
            db.execute('INSERT INTO conversations VALUES (?,?,?)', (cid, json.dumps(state), updated))

    def rows(self, **kwargs):
        return {row['id']: row for row in self.app.conversations(**kwargs)['conversations']}

    def test_a_resolved_place_reaches_the_ledger_with_its_coordinates(self):
        rows = self.rows()
        self.assertEqual(rows['a1']['place']['label'], 'Ahmedabad, Gujarat')
        self.assertEqual(rows['a1']['place']['latitude'], 23.02)
        # The second shape the engine writes: a coordinates object rather than flat fields.
        self.assertEqual(rows['a3']['place'], {'label': 'Kochi, Kerala', 'latitude': 9.93, 'longitude': 76.26})

    def test_a_conversation_that_resolved_no_point_carries_no_place(self):
        rows = self.rows()
        self.assertNotIn('place', rows['a2'])
        # And it is still not inferred from the words: the row is found by text, and still has no place.
        self.assertEqual(rows['a2']['opening_question'], 'Tell me about the fishing season in Surat.')

    def test_search_reaches_the_turns_and_says_which_one_matched(self):
        hit = self.app.conversations(q='coastal')['conversations']
        self.assertEqual([row['id'] for row in hit], ['a2'])
        self.assertEqual(hit[0]['match']['role'], 'assistant')
        self.assertIn('Surat is a coastal district', hit[0]['match']['text'])
        self.assertFalse(hit[0]['match_question'])

    def test_search_matches_the_opening_question_and_says_so(self):
        hit = self.app.conversations(q='wave height')['conversations']
        self.assertEqual([row['id'] for row in hit], ['a3'])
        self.assertTrue(hit[0]['match_question'])

    def test_search_that_matches_nothing_returns_no_rows_and_echoes_the_query(self):
        report = self.app.conversations(q='snow depth')
        self.assertEqual(report['conversations'], [])
        self.assertEqual(report['query'], 'snow depth')
        self.assertOnEmptyLedger()

    def assertOnEmptyLedger(self):
        # No query: everything, newest first, and each with whatever place its own answers resolved.
        report = self.app.conversations()
        self.assertEqual([row['id'] for row in report['conversations']], ['a1', 'a2', 'a3'])
        self.assertIsNone(report['query'])

    def test_a_search_needle_is_trimmed_and_left_as_the_reader_typed_it(self):
        report = self.app.conversations(q='  Surat   season  ')
        self.assertEqual(report['query'], 'Surat season')
        self.assertEqual(report['conversations'], [])


if __name__ == '__main__':
    unittest.main()
