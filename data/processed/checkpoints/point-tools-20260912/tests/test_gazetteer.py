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

if __name__=='__main__':unittest.main()
