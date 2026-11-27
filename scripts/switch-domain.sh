#!/usr/bin/env bash
# 独自ドメインへ切り替える（ドメイン購入・APIトークンへのZone権限追加のあとに1回だけ実行）
#   bash scripts/switch-domain.sh beyond-unlimited-ranking.com
# 1. ドメインがCloudflareで有効か確認（無効ならここで止まり、何も変えない）
# 2. site.json の siteUrl / reportUrl を新ドメインに書き換え
# 3. いつもの公開（テスト→ビルド→D1→デプロイ。独自ドメインと workers.dev からの転送が付く）
# 4. 新URLの表示・フォーム・旧URLからの転送を確認
# 公開に失敗したら site.json を元に戻す。成功後の git commit は手で行う。
set -euo pipefail
cd "$(dirname "$0")/.."

DOMAIN="${1:?使い方: bash scripts/switch-domain.sh <ドメイン>}"
export CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-${cloudflare_API_TOKEN:-}}"
export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-${cloudflare_account_ID:-}}"
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN を設定してください}"

echo "== $DOMAIN の確認"
zone=$(curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/zones?name=$DOMAIN" \
  | python3 -c 'import json,sys;r=json.load(sys.stdin).get("result") or [];print(r[0]["status"] if r else "")')
if [ "$zone" != "active" ]; then
  echo "$DOMAIN がCloudflareで有効になっていません（状態: ${zone:-見つからない}）。" >&2
  echo "購入が済んでいるか、APIトークンにこのドメインの Zone/Zone/Read・Zone/DNS/Edit・Zone/Workers Routes/Edit があるか確認してください。" >&2
  exit 1
fi

OLD_URL=$(python3 -c 'import json;print(json.load(open("site.json"))["siteUrl"])')
cp site.json site.json.bak
restore() { mv site.json.bak site.json; echo "公開に失敗したので site.json を元に戻しました" >&2; }
trap restore ERR

echo "== site.json を https://$DOMAIN/ に変更"
python3 - "$DOMAIN" <<'PY'
import json,sys
d=sys.argv[1];raw=open('site.json').read();s=json.loads(raw)
s['siteUrl']=f'https://{d}/';s['reportUrl']=f'https://{d}/report'
open('site.json','w').write(json.dumps(s,ensure_ascii=False,indent=2)+('\n' if raw.endswith('\n') else ''))
PY

CF_CUSTOM_DOMAIN="$DOMAIN" npm run deploy:cloudflare

trap - ERR
rm -f site.json.bak

echo "== 公開後の確認（証明書の発行に数分かかることがある）"
ok=0
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN/" || true)
  if [ "$code" = "200" ]; then ok=1; break; fi
  sleep 10
done
[ "$ok" = 1 ] && echo "https://$DOMAIN/ → 200" || echo "https://$DOMAIN/ がまだ開けません（最後の応答: $code）。数分後に再確認してください" >&2
echo "/report → $(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN/report")"
echo "旧URL ${OLD_URL} → $(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' "$OLD_URL")"
echo "他サイトからの報告送信（403なら正常）→ $(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'origin: https://evil.example' -H 'content-type: application/json' -d '{}' "https://$DOMAIN/api/reports")"
echo "完了。site.json と生成物を git commit してください。"
