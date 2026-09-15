"""Three repairs found by the operations measurement of 15 September 2026.

1. A model that returned no plan object crashed the turn with AttributeError; it is refused with
   a reason instead, after the repair attempt, so the reader gets an honest answer.
2. A named settlement was not grounded for the published-advisory path, so "...in Ahmedabad" was
   answered by asking which district and state was meant. The tool now resolves the place it was
   given, and discloses the resolution.
3. The publisher directory spells a district differently from the catalogue (Ahmedabad against
   Ahmadabad), and an exact comparison refused a district that exists. Resolution is bounded to
   the directory snapshot, requires a close name that is clearly ahead, and is disclosed.
"""
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from weathergpt_data import document_tools
from weathergpt_data.gazetteer import Gazetteer
from weathergpt_data.language import interpret_plan
from weathergpt_data.transport import SourceError

NOW = datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc)


def stub_engine():
    return SimpleNamespace(gazetteer=Gazetteer(),
                           workspace=SimpleNamespace(service=SimpleNamespace(raw_root=Path('/tmp/weathergpt-test'))))


def advisory_task(place_kind='unknown', name='Ahmedabad'):
    plan = {'places': [{'name': name, 'state': '', 'district': '', 'kind': place_kind}]}
    task = {'request_quote': 'What does the district agromet advisory say for cotton in ' + name + '?',
            'kind': 'agriculture', 'operation': 'lookup', 'parameters': ['agricultural_advisory'],
            'document_request': {'query': 'advisory for cotton', 'crop': 'cotton', 'growth_stage': '', 'topic': 'general',
                                 'mode': 'source_lookup'}}
    return plan, task


class MissingPlanTests(unittest.TestCase):
    def test_a_model_that_returns_no_plan_is_refused_after_the_repair_attempt(self):
        calls = []

        def complete(system, user, schema, max_tokens=1100):
            calls.append(user)
            return None, {'provider': 'stub'}

        with self.assertRaises(SourceError) as caught:
            interpret_plan(complete, 'And what about the afternoon?', NOW, [])
        self.assertEqual(len(calls), 2, 'the repair attempt happens, then the turn is refused')
        self.assertIn('no plan object', str(caught.exception))

    def test_a_model_that_returns_a_list_is_refused_the_same_way(self):
        def complete(system, user, schema, max_tokens=1100):
            return [{'kind': 'forecast'}], {'provider': 'stub'}

        with self.assertRaises(SourceError) as caught:
            interpret_plan(complete, 'And what about the afternoon?', NOW, [])
        self.assertIn('no plan object', str(caught.exception))


class PublisherNameTests(unittest.TestCase):
    def test_a_near_spelling_resolves_to_the_publishers_own_name(self):
        state, district, why = document_tools.match_publisher('Gujarat', 'Ahmadabad')
        self.assertEqual((state, district), ('Gujarat', 'Ahmedabad'))
        self.assertIn('publisher directory spells it Ahmedabad', why)

    def test_an_exact_name_is_returned_unchanged_and_says_so(self):
        state, district, why = document_tools.match_publisher('Gujarat', 'Ahmedabad')
        self.assertEqual((state, district), ('Gujarat', 'Ahmedabad'))
        self.assertIn('spells both names as asked', why)

    def test_a_name_that_is_not_close_enough_is_refused_rather_than_guessed(self):
        state, district, why = document_tools.match_publisher('Gujarat', 'Zzzzzz')
        self.assertIsNone(state)
        self.assertIsNone(district)
        self.assertIn('close enough', why)


class AdvisoryPlaceTests(unittest.TestCase):
    def resolve_with(self, plan, task, result=None):
        """Run the resolution part of the tool by stopping it where it reaches the network."""
        captured = {}

        class StopHere(Exception):
            pass

        def fake_sync(workspace, state, district, index):
            captured.update(state=state, district=district)
            raise StopHere(state + '|' + district)

        packet = result if result is not None else {'question': task['request_quote'], 'notes': []}
        with patch.object(document_tools, 'sync', fake_sync):
            with self.assertRaises(StopHere) as caught:
                document_tools.execute_document(stub_engine(), packet, plan, task)
        captured['packet'] = packet
        captured['stopped'] = str(caught.exception)
        return captured

    def test_a_named_city_is_read_as_its_district_without_asking_the_reader(self):
        plan, task = advisory_task()
        captured = self.resolve_with(plan, task)
        self.assertEqual(captured['stopped'], 'Gujarat|Ahmedabad')
        self.assertTrue(any('publisher directory' in note for note in captured['packet']['notes']),
                        'the resolution is disclosed: ' + str(captured['packet']['notes']))

    def test_a_place_that_cannot_be_grounded_still_asks_rather_than_inventing_a_district(self):
        plan, task = advisory_task(name='Zzzzzz')
        packet = {'question': task['request_quote'], 'notes': []}
        result = document_tools.execute_document(stub_engine(), packet, plan, task)
        self.assertEqual(result['status'], 'needs_clarification')
        self.assertEqual(result['pending_slots'][0]['field'], 'place')

    def test_a_named_district_carries_its_own_state_from_the_directory(self):
        plan, task = advisory_task(place_kind='district', name='Ahmedabad')
        captured = self.resolve_with(plan, task)
        self.assertEqual(captured['stopped'], 'Gujarat|Ahmedabad')


if __name__ == '__main__':
    unittest.main()