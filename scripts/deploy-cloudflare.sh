#!/usr/bin/env bash
# Cloudflare Workers + D1 へ公開する。
# 必要な環境変数:
#   CLOUDFLARE_API_TOKEN   Workers Scripts:Edit と D1:Edit 権限のAPIトークン
#   CLOUDFLARE_ACCOUNT_ID  CloudflareのアカウントID
#   CF_D1_DATABASE_ID      `wrangler d1 create` で作ったDBのID
# 任意: CF_WORKER_NAME（既定 unlimited-beyond-ranking）, CF_D1_DATABASE_NAME（既定 unlimited-beyond-ranking-reports）
#       CF_CUSTOM_DOMAIN（例 beyond-unlimited-ranking.com。設定するとWorkerに独自ドメインを付け、workers.devから転送）
set -euo pipefail
cd "$(dirname "$0")/.."

# 環境側の変数名が小文字混じりでも拾う。D1のIDは秘密ではないので既定値を持つ
export CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-${cloudflare_API_TOKEN:-}}"
export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-${cloudflare_account_ID:-}}"
export CF_D1_DATABASE_ID="${CF_D1_DATABASE_ID:-da2819a7-e34b-4178-a706-a7bdd73217b6}"
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN を設定してください}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID を設定してください}"
: "${CF_D1_DATABASE_ID:?CF_D1_DATABASE_ID を設定してください}"
export CF_WORKER_NAME="${CF_WORKER_NAME:-unlimited-beyond-ranking}"
export CF_D1_DATABASE_NAME="${CF_D1_DATABASE_NAME:-unlimited-beyond-ranking-reports}"

# site.json の公開URLが workers.dev 以外なら、そのドメインを独自ドメインとして使う
if [ -z "${CF_CUSTOM_DOMAIN:-}" ]; then
  CF_CUSTOM_DOMAIN=$(python3 -c 'import json,urllib.parse as u;h=u.urlparse(json.load(open("site.json"))["siteUrl"]).hostname or "";print("" if h.endswith(".workers.dev") else h)')
fi
export CF_CUSTOM_DOMAIN="${CF_CUSTOM_DOMAIN:-}"
if [ -n "$CF_CUSTOM_DOMAIN" ]; then
  echo "== 独自ドメインの確認: $CF_CUSTOM_DOMAIN"
  # ドメインがこのCloudflareアカウントにあり、トークンで見えること
  zone=$(curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/zones?name=$CF_CUSTOM_DOMAIN" \
    | python3 -c 'import json,sys;r=json.load(sys.stdin).get("result") or [];print(r[0]["status"] if r else "")')
  if [ "$zone" != "active" ]; then
    echo "$CF_CUSTOM_DOMAIN がCloudflareで有効になっていない（状態: ${zone:-見つからない}）。ドメイン購入とトークンの Zone 権限を確認してください" >&2
    exit 1
  fi
  # 公開URLの設定が新ドメインになっていること（canonical・OGP・sitemap用）
  if ! python3 -c 'import json,sys,urllib.parse as u;s=json.load(open("site.json"));sys.exit(0 if u.urlparse(s["siteUrl"]).hostname==sys.argv[1] else 1)' "$CF_CUSTOM_DOMAIN"; then
    echo "site.json の siteUrl が $CF_CUSTOM_DOMAIN になっていません。先に書き換えてください" >&2
    exit 1
  fi
fi

echo "== テスト"
python3 -m unittest test_build
node test_scores.cjs
node test_reports.cjs

echo "== 生成・ビルド"
python3 prepare_web.py
if ! grep -q '^エラー 0件' build_report.txt; then
  echo "build_report.txt にエラーがあるので公開を中止します" >&2
  exit 1
fi
npm run build

CONFIG=dist/server/wrangler.json
WRANGLER=./node_modules/wrangler/bin/wrangler.js

echo "== D1 マイグレーション（未適用分のみ）"
# migrations_dir はビルド後の設定ファイルから見た相対パスになるので絶対パスに直す
node -e '
const fs=require("fs");const p=process.argv[1];const c=JSON.parse(fs.readFileSync(p));
for(const d of c.d1_databases||[])d.migrations_dir=require("path").resolve("drizzle");
fs.writeFileSync(p,JSON.stringify(c));' "$CONFIG"
node "$WRANGLER" d1 migrations apply "$CF_D1_DATABASE_NAME" --remote --config "$CONFIG"

echo "== デプロイ"
node "$WRANGLER" deploy --config "$CONFIG"

# 修正報告のメール通知用キー。環境変数にあるときだけ Worker のシークレットへ登録する
RESEND_API_KEY="${RESEND_API_KEY:-${resend_API_KEY:-}}"
if [ -n "$RESEND_API_KEY" ]; then
  echo "== メール通知キーを登録"
  printf '%s' "$RESEND_API_KEY" | node "$WRANGLER" secret put RESEND_API_KEY --config "$CONFIG"
fi
