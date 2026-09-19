import json,sqlite3,tempfile,unittest,zipfile
from pathlib import Path
from weathergpt_data.gazetteer import build,Gazetteer

class GazetteerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.archive=self.root/'IN.zip';self.output=self.root/'built/places.sqlite'
    def row(self,id,name,code='PPL',state='09',district='1',lat='23',aliases=''):
        return '\t'.join([str(id),name,name,aliases,lat,'72','A' if code.startswith('ADM') else 'P',code,'IN','',state,district,'','','0','','0','Asia/Kolkata','2026-09-12'])
    def make(self,bad=False):
        rows=[self.row(1,'State of Gujarāt','ADM1'),self.row(2,'Ahmadābād','ADM2'),
              self.row(3,'Ahmedabad',aliases='અમદાવાદ,Ahmedābād'),self.row(4,'State of Uttar Pradesh','ADM1',state='36'),
              self.row(5,'Ahmedabad',state='36',lat='999' if bad else '24')]
        with zipfile.ZipFile(self.archive,'w') as z:z.writestr('IN.txt','\n'.join(rows))
    def test_aliases_and_same_name_places_keep_source_identity(self):
        self.make();meta=build(self.archive,self.output);g=Gazetteer(self.output)
        self.assertEqual(meta['settlement_records'],2)
        self.assertEqual(len(g.search('Ahmedabad')),2)
        self.assertEqual(len(g.search('Ahmedabad','Gujarat')),1)
        self.assertEqual(g.search('અમદાવાદ')[0]['id'],'3')
        self.assertEqual(g.search('State of Gujarāt'),[])
    def test_modified_catalogue_is_not_used_after_initial_verification(self):
        self.make();build(self.archive,self.output);g=Gazetteer(self.output)
        with sqlite3.connect(self.output) as db:db.execute('UPDATE places SET latitude=0')
        with self.assertRaises(ValueError):g.search('Ahmedabad')
    def test_invalid_input_never_publishes_partial_database(self):
        self.make(bad=True)
        with self.assertRaises(ValueError):build(self.archive,self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.output.parent.glob('.building-*')))

class SeatPreferenceTests(unittest.TestCase):
    """A supplied state plus one administrative seat answers the question; peers still ask.

    These run against the real vendored catalogue, which is the only place the seat order
    exists. They take no measurement of GeoNames beyond what the archive already records.
    """

    @classmethod
    def setUpClass(cls):
        from weathergpt_data.gazetteer import Gazetteer
        cls.gazetteer = Gazetteer()

    def choose(self, name, state=''):
        return Gazetteer.preferred(self.gazetteer.search(name, state))

    def matches_for(self, name, state=''):
        return self.gazetteer.search(name, state)

    def test_a_district_seat_outranks_villages_sharing_the_name(self):
        from weathergpt_data.gazetteer import Gazetteer
        chosen, why = self.choose('Patna', 'Bihar')
        self.assertGreater(len(self.matches_for('Patna', 'Bihar')), 1, 'the fixture must be a shared name')
        self.assertIsNotNone(chosen, 'the district seat must be preferred: ' + why)
        self.assertEqual(chosen['name'], 'Patna')
        self.assertEqual(chosen['admin2'], 'Patna')
        self.assertEqual(chosen['admin1'], 'State of Bihar')
        self.assertEqual(chosen['feature'], 'PPLA')
        self.assertIn('administrative seat', why)

    def test_peer_places_of_the_same_order_still_ask(self):
        chosen, why = self.choose('Kochi')
        self.assertIsNone(chosen, 'villages sharing a name must not be guessed')
        self.assertIn('same order', why)

    def test_a_lone_place_is_the_only_match(self):
        chosen, why = self.choose('Ahmedabad', 'Gujarat')
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen['admin1'], 'State of Gujarāt')
        self.assertIn('only place', why)

    def test_a_town_whose_own_district_carries_its_name_is_preferred(self):
        # Ahmedabad in Gujarat is published in the district of the same name; the other
        # Ahmedabad in the catalogue sits in District Rampur, Uttar Pradesh.
        chosen, why = self.choose('Ahmedabad')
        self.assertIsNotNone(chosen, 'the district-name rule must decide this one: ' + why)
        self.assertEqual(chosen['admin1'], 'State of Gujarāt')
        self.assertIn('district carries the same name', why)

    def test_ranking_is_stable_and_seat_first(self):
        from weathergpt_data.gazetteer import Gazetteer
        matches = self.gazetteer.search('Patna', 'Bihar')
        ranked = Gazetteer.rank_matches(matches)
        ranks = [Gazetteer.feature_rank(item.get('feature')) for item in ranked]
        self.assertEqual(ranks, sorted(ranks), 'candidates are ordered seat first')
        self.assertEqual([item['id'] for item in ranked], [item['id'] for item in Gazetteer.rank_matches(matches)],
                         'ranking is deterministic for the same input')


if __name__=='__main__':unittest.main()


def test_a_catalogue_id_is_ordered_as_a_number_not_as_a_string():
    """Five places are named Kochi and all five are PPL, so seat order ties and the id decides.

    Comparing the ids as strings put `geonames:10453626` before `geonames:1273874` — a lexicographic
    comparison of a number, which means nothing — and offered four Maharashtra villages ahead of the
    Kerala port to anyone who asked about Kochi.

    This checks the comparison, not a prominence ranking: this gazetteer carries no population, and
    nothing here claims to know which Kochi is larger.
    """
    from weathergpt_data.gazetteer import catalogue_key, rank_matches

    kochis = [
        {"id": "geonames:10453626", "feature": "PPL", "admin1": "State of Mahārāshtra"},
        {"id": "geonames:10454487", "feature": "PPL", "admin1": "State of Mahārāshtra"},
        {"id": "geonames:10518944", "feature": "PPL", "admin1": "State of Mahārāshtra"},
        {"id": "geonames:10574547", "feature": "PPL", "admin1": "State of Mahārāshtra"},
        {"id": "geonames:1273874", "feature": "PPL", "admin1": "State of Kerala"},
    ]
    assert [match["id"] for match in rank_matches(kochis)][0] == "geonames:1273874"

    # The ordering is by number, so a longer id is not automatically later.
    assert catalogue_key("geonames:1273874") < catalogue_key("geonames:10453626")
    # A seat still outranks a plain village whatever the ids are.
    seat = {"id": "geonames:9999999", "feature": "PPLA", "admin1": "X"}
    village = {"id": "geonames:1", "feature": "PPL", "admin1": "X"}
    assert [match["id"] for match in rank_matches([village, seat])][0] == "geonames:9999999"
    # An id that is not numeric still orders deterministically rather than raising.
    assert catalogue_key("osm:relation/12") == (1, 0, "osm:relation/12")


def test_a_place_with_no_district_is_not_labelled_with_an_empty_one():
    """Delhi is a state seat with no district, and the label was built by joining three parts always.

    A reader asking about air quality there was answered with "Delhi, , National Capital Territory of
    Delhi" — the empty middle visible in the answer's own opening line. The label is used for display, for
    matching and for the provenance under a claim, so the gap showed up in all three.
    """

    def label(name, admin2, admin1):
        return ', '.join(part for part in (name, admin2, admin1) if str(part or '').strip())

    assert label('Delhi', '', 'National Capital Territory of Delhi') == 'Delhi, National Capital Territory of Delhi'
    assert label('Surat', 'Sūrat', 'State of Gujarāt') == 'Surat, Sūrat, State of Gujarāt'
    assert ', ,' not in label('Delhi', None, 'National Capital Territory of Delhi')

    # And the rule as the catalogue itself applies it, so this cannot drift from the source.
    import inspect
    from weathergpt_data import gazetteer
    built = inspect.getsource(gazetteer.Gazetteer.search)
    assert "if str(part or '').strip()" in built, 'the label join no longer filters empty parts'
