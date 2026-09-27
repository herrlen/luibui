import type { NextConfig } from "next";

// The API is reached through this app so the session cookie stays host-only on app.luibui.com
// (CLAUDE.md rule 11). On the public site only the quick scan routes are passed through.
// Evaluated at build time; the service name "api" resolves in Compose and on mittwald.
const API = process.env.API_INTERNAL_URL ?? "http://api:8000";

const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  ...(process.env.NODE_ENV === "production" ? [{ key: "Content-Security-Policy", value: csp }] : []),
];

const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  experimental: {
    // Uploads are proxied to the API; without this Next.js cuts request bodies at 10 MB. The API
    // itself refuses more than 60 MB (UPLOAD_MAX_BYTES) before reading the body.
    middlewareClientMaxBodySize: "61mb",
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/api/v1/:path*",
          has: [{ type: "host", value: "app\\..*" }],
          destination: `${API}/api/v1/:path*`,
        },
        { source: "/api/v1/quickscans", destination: `${API}/api/v1/quickscans` },
        { source: "/api/v1/quickscans/:id", destination: `${API}/api/v1/quickscans/:id` },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default config;
