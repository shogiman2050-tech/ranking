from pathlib import Path
import json,html,shutil,subprocess
subprocess.run(['python','build_public.py'],check=True)
p=Path('.')
(p/'app/ranking-html.ts').write_text('export default '+json.dumps((p/'dist/index.html').read_text(),ensure_ascii=False)+';')
for f in (p/'dist').iterdir():
 if f.is_file() and f.name!='index.html':shutil.copy2(f,p/'public'/f.name)
seasons=json.loads((p/'players.json').read_text())['seasons']
report=(p/'report.html').read_text().replace('__SEASONS__',''.join('<option>'+html.escape(s)+'</option>' for s in seasons))
(p/'app/report/content.ts').write_text('export default '+json.dumps(report,ensure_ascii=False)+';')
(p/'app/report/route.ts').write_text('import html from "./content"; export function GET(){return new Response(html,{headers:{"Content-Type":"text/html; charset=utf-8"}})}')
