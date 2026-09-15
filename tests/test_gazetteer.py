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
