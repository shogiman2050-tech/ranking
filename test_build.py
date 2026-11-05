import json
import unittest
from build_public import ROOT, prepare

class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT/'players.json').read_text())
        self.row = dict(season=self.config['seasons'][0], className='エルフ', name='テスト人物', cr=1900, rank=1)
    def test_duplicate_rejected(self):
        self.assertTrue(prepare([self.row, self.row], self.config)[1])
    def test_same_name_conflict_rejected(self):
        self.assertTrue(prepare([self.row, dict(self.row, rank=2, cr=1890)], self.config)[1])
    def test_a_merged(self):
        a=dict(self.row, name='あ'); b=dict(a, rank=2, cr=1890)
        rows, errors, _=prepare([a,b], self.config)
        self.assertFalse(errors)
        self.assertEqual(rows[0]['personKey'], rows[1]['personKey'])
    def test_other_short_names_merge(self):
        for name in ['光里', 'K', 'あい']:
            a=dict(self.row,name=name)
            b=dict(a,season=self.config['seasons'][1])
            rows,errors,_=prepare([a,b],self.config)
            self.assertFalse(errors)
            self.assertEqual(rows[0]['personKey'],rows[1]['personKey'])
            self.assertFalse(any(r.get('separated') for r in rows))
    def test_ties_have_no_gap_warning(self):
        rows=[self.row,dict(self.row,name='別の人物'),dict(self.row,name='第三の人物',rank=3,cr=1890)]
        self.assertFalse(any('順位欠落' in n for n in prepare(rows,self.config)[2]))
    def test_pending_alias_not_merged(self):
        for group in self.config['aliases']:
            if group['canonical']=='Starle': group['confirmed']=False
        rows=[dict(self.row,name='Starlie'),dict(self.row,name='Starle',rank=2,cr=1890)]
        out,_,_=prepare(rows,self.config)
        self.assertNotEqual(out[0]['personKey'],out[1]['personKey'])
    def test_all_records_preserved(self):
        raw=json.loads((ROOT/'records.json').read_text()); out, errors, _=prepare(raw,self.config)
        self.assertFalse(errors); self.assertEqual(len(out),2376)
        aa=[r for r in out if r['name']=='あ']
        self.assertEqual(1,len({r['personKey'] for r in aa}))
        mishadow=[r for r in out if r['name']=='頑張れMishadow']
        self.assertEqual(len(mishadow),12)
        self.assertEqual(len({r['personKey'] for r in mishadow}),1)

if __name__=='__main__': unittest.main()
