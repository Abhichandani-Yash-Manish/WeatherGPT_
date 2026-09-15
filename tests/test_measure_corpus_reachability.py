"""The evidence CLI must write its requested run without changing an earlier record."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import measure_corpus_reachability as measure


class MeasurementCommandTests(unittest.TestCase):
    def test_custom_question_writes_the_requested_file_and_section_counts(self):
        class Engine:
            def ask(self, request):
                self.question = request['question']
                return {'status': 'partial', 'answer': 'A bounded reading', 'passages': [1, 2],
                        'whole_document': {'sections_indexed': 18, 'sections_served': 12},
                        'retrieval_coverage': [{'sections_listed': 18}]}
        engine = Engine()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'new' / 'reading.json'
            with patch.object(measure, 'Workspace'), patch.object(measure, 'ConversationEngine', return_value=engine), \
                    patch('sys.argv', ['measure', '--question', 'Read the national bulletin', '--output', str(output)]), \
                    contextlib.redirect_stdout(io.StringIO()):
                measure.main()
            record = json.loads(output.read_text())
        self.assertEqual(engine.question, 'Read the national bulletin')
        self.assertEqual(record['summary']['partial'], 1)
        self.assertEqual(record['rows'][0]['sections_listed'], 18)
        self.assertEqual(record['rows'][0]['sections_served'], 12)

    def test_a_failed_question_does_not_discard_the_next_result(self):
        class Engine:
            def ask(self, request):
                if request['question'] == 'first':
                    raise RuntimeError('fixture failure')
                return {'status': 'unavailable', 'answer': 'No indexed edition'}
        rows = []
        with contextlib.redirect_stdout(io.StringIO()):
            measure.run(Engine(), rows, ['first', 'second'])
        summary = measure.summarise(rows)
        self.assertEqual(summary['journeys'], 2)
        self.assertEqual(summary['errors'], 1)
        self.assertEqual(summary['unavailable'], 1)
        self.assertIn('fixture failure', rows[0]['error'])
