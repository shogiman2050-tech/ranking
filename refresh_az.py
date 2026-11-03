"""Replace the Azvaldt first-half records with the attached video transcription."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fresh_az_data import groups

path = Path(__file__).with_name('records.json')
season = 'アズヴォルト・レヴナント 前半'
records = [r for r in json.loads(path.read_text()) if r['season'] != season]
for cls, entries in groups.items():
    next_rank = 1
    previous_cr = float('inf')
    names_seen = set()
    for rank, cr, *names in entries:
        assert rank == next_rank, (cls, rank, next_rank)
        assert cr <= previous_cr, (cls, rank, cr)
        for name in names:
            assert name not in names_seen or (cls == 'ウィッチ' and name == 'あ'), (cls, name)
            names_seen.add(name)
            record = dict(season=season, mode='アンリミ', className=cls,
                          rank=rank, name=name, cr=cr,
                          source='1000006118.mp4', status='確認済み')
            if cls == 'ウィッチ' and name == 'あ' and rank == 57:
                record['personKey'] = '同名区別:ウィッチ:57:あ'
            records.append(record)
        next_rank += len(names)
        previous_cr = cr
path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
print(f'Updated {sum(len(v) - 2 for entries in groups.values() for v in entries)} Azvaldt records, {len(records)} total')
