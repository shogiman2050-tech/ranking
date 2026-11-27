from pathlib import Path
import json,html,re,shutil,subprocess
subprocess.run(['python','build_public.py'],check=True)
p=Path('.')
(p/'app/ranking-html.ts').write_text('export default '+json.dumps((p/'dist/index.html').read_text(),ensure_ascii=False)+';')
for f in (p/'dist').iterdir():
 if f.is_file() and f.name!='index.html':shutil.copy2(f,p/'public'/f.name)
seasons=json.loads((p/'players.json').read_text())['seasons']
report=(p/'report.html').read_text().replace('__SEASONS__',''.join('<option>'+html.escape(s)+'</option>' for s in seasons))
(p/'app/report/content.ts').write_text('export default '+json.dumps(report,ensure_ascii=False)+';')

# 共通の小さなフッター（修正報告・お問い合わせ・プライバシーポリシー）
FOOTER = ('<nav class="sub" aria-label="サイト内リンク"><a href="/">ランキング</a><a href="/report">修正報告</a>'
          '<a href="/contact">お問い合わせ</a><a href="/privacy">プライバシーポリシー</a></nav>'
          '<p class="sub-note">運営：ゆらゆら／株式会社Cygamesとは関係のない非公式ファンサイトです。</p>')
SUB_CSS = ('.sub{display:flex;flex-wrap:wrap;gap:6px 16px;margin:40px 0 6px;padding-top:16px;border-top:1px solid currentColor;'
           'border-top-color:color-mix(in srgb,currentColor 18%,transparent);font-size:13px}.sub-note{font-size:12px;margin:0}'
           '.doc h2{font-size:18px;margin:32px 0 6px}.doc p{line-height:1.9}.doc code{font-size:.9em}')
def with_footer(body):
    return body.replace('<!--FOOTER-->', FOOTER)
# 修正報告ページにもフッターを付ける
(p/'app/report/content.ts').write_text('export default '+json.dumps(with_footer(report.replace('</form></main>', '</form><!--FOOTER--></main>')).replace('</style><style id="themeClassic"', SUB_CSS+'</style><style id="themeClassic"').replace('</style><script>try', SUB_CSS+'</style><script>try'), ensure_ascii=False)+';')
# プライバシーポリシー・お問い合わせ：修正報告ページと同じ見た目（head部分）を使う
shell = report[:report.index('<main>')]
shell = shell.replace('</style><style id="themeClassic"', SUB_CSS+'</style><style id="themeClassic"').replace('</style><script>try', SUB_CSS+'</style><script>try')
for name, title in (('privacy', 'プライバシーポリシー'), ('contact', 'お問い合わせ')):
    head = re.sub(r'<title>.*?</title>', '<title>'+html.escape(title)+' | アンリミ ビヨンドランキング</title>', shell, count=1)
    page = head + with_footer((p/(name+'.html')).read_text()) + '</html>'
    (p/'app'/name).mkdir(exist_ok=True)
    (p/'app'/name/'content.ts').write_text('export default '+json.dumps(page, ensure_ascii=False)+';')
