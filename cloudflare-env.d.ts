declare namespace Cloudflare {
  interface Env {
    DB?: D1Database;
    BUCKET?: R2Bucket;
    // 修正報告のメール通知（Resend）。両方そろったときだけ送る
    RESEND_API_KEY?: string;
    REPORT_EMAIL_TO?: string;
  }
}
