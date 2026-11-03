"""Validate every source row; resolve only confirmed identities; never drop records."""
import hashlib
import json
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLASSES = ['エルフ', 'ロイヤル', 'ウィッチ', 'ドラゴン', 'ナイトメア', 'ビショップ', 'ネメシス']

def record_id(row):
    fields = [row.get(k) for k in ('season', 'className', 'name', 'rank', 'cr', 'source')]
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False).encode()).hexdigest()[:20]

def prepare(rows, config):
    errors, notes, result = [], [], []
    aliases = {}
    for group in config['aliases']:
        if not group.get('confirmed'):
            notes.append('未確認の別名候補（未統合）: ' + ' / '.join([group['canonical']] + group['names']))
            continue
        for name in [group['canonical']] + group['names']:
            if name in aliases and aliases[name] != group['canonical']:
                errors.append('別名の競合: ' + name)
            aliases[name] = group['canonical']
    allowed_multiple = {'name:' + g['canonical'] for g in config['aliases'] if g.get('confirmed') and g.get('allow_multiple_records_per_slot')}
    seen_ids, identities, groups, names = set(), defaultdict(list), defaultdict(list), defaultdict(set)
    for raw in rows:
        r = dict(raw)
        rid = record_id(r)
        if rid in seen_ids:
            errors.append('完全重複: ' + str(raw))
        seen_ids.add(rid)
        if r['season'] not in config['seasons'] or r['className'] not in CLASSES:
            errors.append('不明な期間・クラス: ' + str(raw))
        if not isinstance(r.get('cr'), int) or r['cr'] < 1850:
            errors.append('不正なCR: ' + str(raw))
        rank = r.get('rank')
        if rank is not None and (type(rank) is not int or rank < 1):
            errors.append('不正な順位: ' + str(raw))
        original = r['name']
        names[unicodedata.normalize('NFKC', original)].add(original)
        r['name'] = aliases.get(original, original)
        if original != r['name']:
            r['rawName'] = original
        explicit = config.get('record_identities', {}).get(rid)
        if explicit:
            key = 'verified:' + explicit
        elif original in aliases:
            key = 'name:' + r['name']
        else:
            key = 'person:' + r['personKey'] if r.get('personKey') else 'name:' + r['name']
        r.update(personKey=key, recordId=rid)
        identities[(r['season'], r['className'], key)].append(r)
        groups[(r['season'], r['className'])].append(r)
        result.append(r)
    for key, members in identities.items():
        if len(members) > 1 and key[2] in allowed_multiple:
            notes.append('ユーザー指定の同名統合（全記録保持・個人集計は枠ごと最高CRを採用）: ' + str(key))
        elif len(members) > 1:
            errors.append('同一期間・クラス・人物の重複（修正または人物ID指定が必要）: ' + str(key))
    for key, members in groups.items():
        same_names = defaultdict(list)
        ranks = defaultdict(list)
        for r in members:
            same_names[r['name']].append(r)
            if type(r.get('rank')) is int and r['rank'] > 0:
                ranks[r['rank']].append(r)
        for name, rr in same_names.items():
            if len(rr) > 1:
                notes.append(f'同名の複数記録を保持: {key} {name} ' + ', '.join(str(r['rank'])+'位' for r in rr))
        expected, previous_cr = 1, None
        for rank, rr in sorted(ranks.items()):
            if rank > expected:
                notes.append(f'順位欠落候補: {key} {expected}〜{rank-1}位相当（同率人数を要確認）')
            elif rank < expected:
                notes.append(f'順位重なり: {key} {rank}位（期待 {expected}位）')
            crs = {r['cr'] for r in rr}
            if len(crs) > 1:
                notes.append(f'同順位でCR不一致: {key} {rank}位 {sorted(crs)}')
            if previous_cr is not None and max(crs) >= previous_cr:
                notes.append(f'CR逆転／同CRの順位不一致: {key} {rank}位')
            previous_cr = min(crs)
            expected = rank + len(rr)
    for normalized, variants in names.items():
        if len(variants) > 1:
            notes.append('NFKC表記ゆれ候補（自動統合しない）: ' + ' / '.join(sorted(variants)))
    return result, errors, notes

def main():
    rows = json.loads((ROOT / 'records.json').read_text())
    config = json.loads((ROOT / 'players.json').read_text())
    data, errors, notes = prepare(rows, config)
    report = '\n'.join([f'原記録 {len(rows)}件 / 出力 {len(data)}件', f'エラー {len(errors)}件', *['ERROR: '+e for e in errors], *notes])+'\n'
    (ROOT / 'build_report.txt').write_text(report)
    print(report)
    if errors:
        raise SystemExit('検査失敗。公開HTMLは更新しません。')
    from publish_assets import publish
    publishing_notes = publish(ROOT, data, config['seasons'])
    with (ROOT / 'build_report.txt').open('a') as report_file:
        report_file.write('\n'.join(publishing_notes)+'\n')

if __name__ == '__main__':
    main()
