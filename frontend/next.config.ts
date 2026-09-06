import type { NextConfig } from "next";

// API origin for client-visible /api/* rewrites. Defaults to the local demo
// API; point API_ORIGIN at another host (e.g. https://apilot.example.com)
// when the FastAPI backend is deployed elsewhere.
const API_ORIGIN = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
