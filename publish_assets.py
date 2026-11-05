import html, json, re, shutil, sys
from datetime import datetime, timedelta, timezone

def publish(ROOT, out, seasons):
    errors, warnings, notes = [], [], []
    site = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
    site_url = site['siteUrl'].strip()
    if not site_url.startswith('https://'):
        errors.append('site.json の siteUrl は https:// で始めてください')
    if not site_url.endswith('/'):
        site_url += '/'
    if errors:
        print('ビルドを中止しました：', *errors, sep='\n  ')
        sys.exit(1)
    updated = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
    data = json.dumps(out, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    season_json = json.dumps(seasons, ensure_ascii=False)
    jsonld = json.dumps({'@context': 'https://schema.org', '@type': 'WebSite', 'name': site['siteName'],
                         'url': site_url, 'description': site['description'], 'inLanguage': 'ja',
                         'dateModified': updated}, ensure_ascii=False).replace('</', '<\\/')
    ga_id = site.get('gaId', '').strip()
    ga = ('<script async src="https://www.googletagmanager.com/gtag/js?id=' + html.escape(ga_id) + '"></script>\n'
          "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}"
          "gtag('js',new Date());gtag('config'," + json.dumps(ga_id) + ");</script>") if ga_id else ''
    report_url = site.get('reportUrl', '').strip()
    report = (f' 改名・記録の誤りは<a href="{html.escape(report_url)}" target="_blank" rel="noopener">こちらのフォーム</a>から教えてください。'
              if report_url else '')
    template = (ROOT / 'page.html').read_text(encoding='utf-8')
    for marker in ('/*__DATA__*/', '/*__SEASONS__*/', '<!--__GA__-->'):
        if marker not in template:
            print(f'page.html に {marker} がありません')
            sys.exit(1)
    suspects = json.dumps(json.loads((ROOT / 'players.json').read_text(encoding='utf-8')).get('suspect_names', []), ensure_ascii=False).replace('</', '<\\/')
    page = (template.replace('/*__SUSPECT__*/', suspects).replace('/*__DATA__*/', data).replace('/*__SEASONS__*/', season_json)
            .replace('<!--__GA__-->', ga).replace('<!--__REPORT__-->', report)
            .replace('<!--__GA_NOTE__-->', 'アクセス解析にGoogle Analyticsを使用しています。' if ga_id else '')
            .replace('{{JSONLD}}', jsonld).replace('{{SITE_URL}}', html.escape(site_url))
            .replace('{{SITE_NAME}}', html.escape(site['siteName']))
            .replace('{{DESCRIPTION}}', html.escape(site['description'])).replace('{{UPDATED}}', updated))
    leftover = re.findall(r'\{\{[A-Z_]+\}\}', page)
    if leftover:
        print('置き換えられていない項目があります：', set(leftover))
        sys.exit(1)

    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    (dist / 'index.html').write_text(page, encoding='utf-8')
    for f in (ROOT / 'static').iterdir():
        if f.is_file():
            shutil.copy2(f, dist / f.name)
    (dist / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {site_url}sitemap.xml\n', encoding='utf-8')
    (dist / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{html.escape(site_url)}</loc><lastmod>{updated}</lastmod></url>\n</urlset>\n', encoding='utf-8')
    (dist / '404.html').write_text(
        '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>ページが見つかりません｜{html.escape(site["siteName"])}</title><meta name="robots" content="noindex">'
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg"><style>body{margin:0;min-height:100vh;display:grid;place-items:center;'
        'background:#0b1425;color:#ecf5fa;font-family:system-ui,sans-serif;text-align:center;padding:16px}a{color:#6cddd8}</style></head>'
        f'<body><div><h1>ページが見つかりません</h1><p><a href="{html.escape(site_url)}">{html.escape(site["siteName"])}のトップへ</a></p></div></body></html>\n',
        encoding='utf-8')
    # Cloudflare Pages / Netlify 用（他のホスティングでは無視される）
    (dist / '_headers').write_text(
        '/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n'
        '  X-Frame-Options: SAMEORIGIN\n\n/\n  Cache-Control: public, max-age=300\n/index.html\n  Cache-Control: public, max-age=300\n'
        '/og.png\n  Cache-Control: public, max-age=86400\n', encoding='utf-8')
    size_kb = (dist / 'index.html').stat().st_size / 1024
    notes.append(f'公開URL：{site_url}　最終更新日：{updated}　index.html {size_kb:.0f}KB')
    if not report_url:
        warnings.append('site.json の reportUrl が空です（改名・誤り報告フォームのリンクが出ません）')

    return notes + warnings
