import json
import unittest
from build_public import ROOT, prepare

class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.full_config = json.loads((ROOT/'players.json').read_text())
        self.config = json.loads((ROOT/'players.json').read_text())
        self.config['person_identities'] = []  # 合成データのテストでは実データ用の人物指定を使わない
        self.row = dict(season=self.config['seasons'][0], className='エルフ', name='テスト人物', cr=1900, rank=1)
    def test_duplicate_rejected(self):
        self.assertTrue(prepare([self.row, self.row], self.config)[1])
    def test_same_name_conflict_rejected(self):
        self.assertTrue(prepare([self.row, dict(self.row, rank=2, cr=1890)], self.config)[1])
    def test_a_split_per_record(self):
        a=dict(self.row, name='あ'); b=dict(a, rank=2, cr=1890)
        rows, errors, _=prepare([a,b], self.config)
        self.assertFalse(errors)
        self.assertNotEqual(rows[0]['personKey'], rows[1]['personKey'])
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
    def test_person_identity_separates_same_name(self):
        a=dict(self.row,name='あ'); b=dict(a,rank=2,cr=1890)
        self.config['person_identities']=[{'id':'X','label':'旧X','records':[dict(season=a['season'],className='エルフ',rank=2,cr=1890,name='あ')]}]
        rows,errors,_=prepare([a,b],self.config)
        self.assertFalse(errors)
        self.assertNotEqual(rows[0]['personKey'],rows[1]['personKey'])
        self.assertEqual(rows[1]['name'],'あ')
    def test_person_identity_unmatched_is_error(self):
        self.config['person_identities']=[{'id':'X','records':[dict(season=self.row['season'],className='エルフ',rank=99,cr=1850,name='誰')]}]
        self.assertTrue(prepare([self.row],self.config)[1])
    def test_old_names_not_published(self):
        raw=json.loads((ROOT/'records.json').read_text()); out,_,_=prepare(raw,self.full_config)
        blob=json.dumps(out,ensure_ascii=False)
        for word in ['もりもりごはんパワー','進藤','ビバチー','でかぱい']:
            self.assertNotIn(word,blob)
    def test_all_records_preserved(self):
        raw=json.loads((ROOT/'records.json').read_text()); out, errors, _=prepare(raw,self.full_config)
        self.assertFalse(errors); self.assertEqual(len(out),2376)
        aa=[r for r in out if r['name']=='あ' and not r['personKey'].startswith('verified:')]
        self.assertEqual(len(aa),len({r['personKey'] for r in aa}))
        mori=[r for r in out if r['personKey'].startswith('verified:') and r['season'].startswith(('クロニクル','アズヴォルト')) and r['className']=='エルフ' and r['name']=='あ']
        self.assertEqual(len(mori),3); self.assertEqual(len({r['personKey'] for r in mori}),1)
        self.assertEqual(len({r['personKey'] for r in out if r['name']=='Player'}),3)
        mishadow=[r for r in out if r['name']=='頑張れMishadow']
        self.assertEqual(len(mishadow),12)
        self.assertEqual(len({r['personKey'] for r in mishadow}),1)

if __name__=='__main__': unittest.main()
