import handler from "vinext/server/fetch-handler";
import { runWithConnectorBinding } from "../lib/connector-context";
import type { ConnectorBinding } from "../lib/connector-contract.mjs";

const worker = {
  fetch(request: Request, env: Cloudflare.Env, ctx: ExecutionContext<{ CONNECTORS?: ConnectorBinding }>) {
    // 独自ドメイン運用時は workers.dev と www. のページ表示を正式URLへ寄せる（フォーム送信などGET/HEAD以外は触らない）
    const canonical = env.CANONICAL_HOST;
    if (canonical && (request.method === "GET" || request.method === "HEAD")) {
      const url = new URL(request.url);
      if ((url.hostname.endsWith(".workers.dev") || url.hostname === `www.${canonical}`) && url.hostname !== canonical) {
        url.protocol = "https:";
        url.hostname = canonical;
        url.port = "";
        return Response.redirect(url.toString(), 301);
      }
    }
    let binding = ctx.props?.CONNECTORS;
    // Local preview emulates the same request-scoped capability. This branch and
    // the auxiliary service binding are absent from production builds.
    if (import.meta.env.DEV && !binding && env.CONNECTORS) {
      const preview = env.CONNECTORS;
      const expiresAt = Date.now() + 60_000;
      binding = {
        async getContext() {
          if (Date.now() >= expiresAt) return { status: "request_context_expired" };
          return preview.getContext?.() ?? { status: "binding_unavailable" };
        },
        async invoke(connectorId, actionName, args) {
          if (Date.now() >= expiresAt) {
            return { status: "request_context_expired", message: "This request has expired. Please try again." };
          }
          return preview.invoke(connectorId, actionName, args);
        },
      };
    }
    return runWithConnectorBinding(binding, () => handler.fetch(request, env, ctx));
  },
};

export default worker;
