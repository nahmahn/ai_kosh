import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Proxy API calls to the FastAPI backend (voice pipeline)
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      { source: "/api/voice/:path*", destination: `${backendUrl}/voice/:path*` },
      { source: "/api/ocr/:path*", destination: `${backendUrl}/ocr/:path*` },
      { source: "/api/fingerprint/:path*", destination: `${backendUrl}/fingerprint/:path*` },
    ];
  },
};

export default nextConfig;
