import vinext from "vinext";
import { defineConfig } from "vite";
import hostingConfig from "./.openai/hosting.json";
import { readExecutionProfile } from "./scripts/execution-profile.mjs";
import { configureToolEnvironment } from "./scripts/tool-environment.mjs";
import { sites } from "./scripts/vite/sites-vite-plugin";
import { connectorPreview } from "./scripts/vite/connector-preview-plugin.mjs";

const SITE_CREATOR_PLACEHOLDER_DATABASE_ID =
  "00000000-0000-4000-8000-000000000000";

const { d1, r2 } = hostingConfig;

// Cloudflare 本番デプロイ用（scripts/deploy-cloudflare.sh が設定する）。
// 未設定ならローカル用のプレースホルダーのまま。
const workerName = process.env.CF_WORKER_NAME || "unlimited-beyond-ranking";
const d1DatabaseName = process.env.CF_D1_DATABASE_NAME || "unlimited-beyond-ranking-reports";
// 独自ドメイン（例: beyond-unlimited-ranking.com）。設定するとWorkerにカスタムドメインを付け、
// workers.dev へのGET/HEADをそのドメインへ301転送する。未設定なら今まで通り。
const customDomain = process.env.CF_CUSTOM_DOMAIN?.trim() || "";
const d1DatabaseId =
  process.env.CF_D1_DATABASE_ID || SITE_CREATOR_PLACEHOLDER_DATABASE_ID;

// macOS Seatbelt blocks FSEvents, so Codex previews need polling for HMR.
const isCodexSeatbeltSandbox = process.env.CODEX_SANDBOX === "seatbelt";
const managedLinux = readExecutionProfile() === "managed-linux";

const localBindingConfig = {
  name: workerName,
  main: "./worker/index.ts",
  compatibility_flags: ["nodejs_compat"],
  ...(customDomain
    ? { routes: [{ pattern: customDomain, custom_domain: true }, { pattern: `www.${customDomain}`, custom_domain: true }], workers_dev: true, vars: { CANONICAL_HOST: customDomain } }
    : {}),
  d1_databases: d1
    ? [
        {
          binding: d1,
          database_name: d1DatabaseName,
          database_id: d1DatabaseId,
          migrations_dir: "drizzle",
        },
      ]
    : [],
  r2_buckets: r2
    ? [
        {
          binding: r2,
          bucket_name: "site-creator-r2",
        },
      ]
    : [],
};

export default defineConfig(async ({ command }) => {
  configureToolEnvironment(process.cwd());

  // Wrangler snapshots its log path while the Cloudflare plugin is imported.
  const { cloudflare } = await import("@cloudflare/vite-plugin");

  return {
    server: {
      ...(managedLinux
        ? { host: "0.0.0.0", allowedHosts: ["terminal.local"] }
        : {}),
      ...(isCodexSeatbeltSandbox
        ? { watch: { useFsEvents: false, usePolling: true } }
        : {}),
    },
    plugins: [
      vinext(),
      sites({ mockAuth: !managedLinux }),
      connectorPreview(),
      cloudflare({
        viteEnvironment: { name: "rsc", childEnvironments: ["ssr"] },
        inspectorPort: false,
        config: {
          ...localBindingConfig,
          ...(command === "serve"
            ? {
                services: [
                  {
                    binding: "CONNECTORS",
                    service: "sites-connector-preview",
                    entrypoint: "ConnectorPreview",
                  },
                ],
              }
            : {}),
        },
        ...(command === "serve"
          ? {
              auxiliaryWorkers: [
                {
                  config: {
                    name: "sites-connector-preview",
                    main: "./scripts/connector-preview/worker.mjs",
                    compatibility_date: "2026-05-15",
                  },
                },
              ],
            }
          : {}),
      }),
    ],
  };
});
