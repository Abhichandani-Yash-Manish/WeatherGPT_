"""Reconciliation between the source registry, the activation ledger and the code.

These checks read recorded files. They take no measurement of their own and they
prove nothing about any publisher: a ledger row states what one bounded probe saw
at one instant, and a reachable address is not a validated product.

The reconciliation that matters here is drift: the ledger must not go on saying a
source has no connector after a family in the code starts ingesting it, and it must
not report a source as reachable from a conversation when only its intake exists.
"""
import json
import unittest
from pathlib import Path

from weathergpt_data.document_ingest import DISTRICT_SPEC, FAMILIES

ROOT = Path(__file__).resolve().parents[1]
LEDGER = json.loads((ROOT / 'data' / 'registry' / 'source-review.json').read_text())
REGISTRY = json.loads((ROOT / 'data' / 'registry' / 'sources.json').read_text())
ROWS = {row['id']: row for row in LEDGER['sources']}
PRODUCTS = {product['id']: product for product in REGISTRY['products']}


def ingesting_families():
    wired = {}
    for name, spec in list(FAMILIES.items()) + [(DISTRICT_SPEC['family'], DISTRICT_SPEC)]:
        wired.setdefault(spec['source_id'], []).append(name)
    return {source: sorted(names) for source, names in wired.items()}


class CoverageTests(unittest.TestCase):
    def test_the_ledger_and_the_registry_describe_the_same_sources(self):
        self.assertEqual(sorted(ROWS), sorted(PRODUCTS),
                         'Every registered source must appear in the ledger and nothing else may.')

    def test_no_source_is_left_unmeasured(self):
        unmeasured = [i for i, row in ROWS.items() if row['status'] == 'unmeasured']
        self.assertEqual(unmeasured, [], 'A source with no recorded measurement is an unexamined source.')

    def test_every_status_is_in_the_declared_vocabulary(self):
        for source_id, row in ROWS.items():
            self.assertIn(row['status'], LEDGER['status_vocabulary'], source_id)
            self.assertEqual(row['status_meaning'], LEDGER['status_vocabulary'][row['status']], source_id)

    def test_the_recorded_counts_match_the_rows(self):
        counted = {}
        for row in ROWS.values():
            counted[row['status']] = counted.get(row['status'], 0) + 1
        self.assertEqual(LEDGER['counts'], counted)

    def test_a_probe_is_recorded_against_the_registered_address(self):
        for source_id, row in ROWS.items():
            if row['status_basis'] != 'probe':
                continue
            probe = row['probe']
            self.assertIsNotNone(probe, source_id)
            self.assertEqual(probe['url'], row['access_url'], source_id)
            self.assertEqual(probe['url'], PRODUCTS[source_id].get('access_url'), source_id)
            self.assertIsNotNone(probe['checked_at_utc'], source_id)

    def test_a_status_without_an_address_is_never_called_a_measurement(self):
        for source_id, row in ROWS.items():
            if row['access_url'] is None:
                self.assertEqual(row['status_basis'], 'curated', source_id)
                self.assertIsNone(row['probe'], source_id)


class ConnectorReconciliationTests(unittest.TestCase):
    def test_every_ingesting_family_is_recorded_against_its_source(self):
        for source_id, families in ingesting_families().items():
            self.assertIn(source_id, ROWS, source_id + ' has a document family but no ledger row')
            connector = ROWS[source_id]['connector']
            self.assertEqual(connector['ingested_by_families'], families, source_id)
            self.assertTrue(connector['connected'],
                            source_id + ' is ingested by ' + ', '.join(families) + ' but the ledger denies it')
            self.assertEqual(connector['kind'], 'document', source_id)

    def test_the_ledger_claims_no_connector_the_code_does_not_have(self):
        wired = ingesting_families()
        for source_id, row in ROWS.items():
            recorded = row['connector']['ingested_by_families']
            self.assertEqual(recorded, wired.get(source_id, []), source_id)

    def test_reaching_a_conversation_is_never_inferred_from_intake(self):
        for source_id, row in ROWS.items():
            connector = row['connector']
            if connector['wired_to_chat']:
                self.assertTrue(connector['connected'],
                                source_id + ' cannot be reachable from chat while having no connector at all')
            if connector['connected'] and not connector['wired_to_chat']:
                self.assertIsNotNone(connector['reachability_note'],
                                     source_id + ' is ingested but not conversational, which must be stated')

    def test_the_corpus_capability_is_derived_into_reachability(self):
        """The ledger must not deny a source the whole-document tool actually serves.

        `scripts/audit_sources.py` derives `wired_to_chat` from `corpus_sources()`, so
        adding a family updates reachability on rebuild. This check reads the recorded
        ledger and fails on the stale denial docs/29 recorded.
        """
        from weathergpt_data.capabilities import corpus_sources
        for source_id in corpus_sources():
            self.assertIn(source_id, ROWS, source_id + ' is served by the corpus tool but has no ledger row')
            self.assertTrue(ROWS[source_id]['connector']['wired_to_chat'],
                            source_id + ' is served by the corpus tool but the ledger denies reachability')


class ApprovalTests(unittest.TestCase):
    def test_the_recorded_approval_covers_local_prototype_use_only(self):
        policy = LEDGER['policy']
        self.assertEqual(policy['review_decision'], 'approved_local_prototype')
        self.assertEqual(policy['redistribution'], 'not_approved')
        self.assertEqual(policy['production_approval'], 'not_granted')

    def test_the_registry_carries_the_same_decision(self):
        for source_id, product in PRODUCTS.items():
            self.assertEqual(product.get('user_review'), 'approved_local_prototype', source_id)
            self.assertEqual(product.get('review_ledger'), 'data/registry/source-review.json', source_id)

    def test_approval_never_becomes_a_claim_of_selection_or_readiness(self):
        note = (LEDGER['policy']['note'] + ' ' + REGISTRY.get('review_policy', '')).lower()
        self.assertIn('registration', note)
        self.assertIn('not', note)
        for overclaim in ('operationally ready', 'production ready', 'validated forecast', 'fully compliant'):
            self.assertNotIn(overclaim, note)

    def test_a_blocked_source_keeps_its_endpoint_and_its_next_action(self):
        blocked = [row for row in ROWS.values() if row['status'] == 'blocked_access']
        self.assertTrue(blocked, 'The credential-gated sources must stay visible, not be quietly dropped.')
        for row in blocked:
            self.assertTrue(row['access_url'], row['id'])
            self.assertTrue(row['next_action'], row['id'])
            self.assertFalse(row['connector']['wired_to_chat'], row['id'])


if __name__ == '__main__':
    unittest.main()
