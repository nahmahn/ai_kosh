import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const voiceUrl = process.env.VOICE_BACKEND_URL || process.env.BACKEND_URL || "http://localhost:8000";
    const ocrUrl = process.env.OCR_BACKEND_URL || "http://localhost:8001";
    return [
      { source: "/api/voice/:path*", destination: `${voiceUrl}/voice/:path*` },
      { source: "/api/ocr/:path*", destination: `${ocrUrl}/ocr/:path*` },
      { source: "/api/fingerprint/:path*", destination: `${voiceUrl}/fingerprint/:path*` },
    ];
  },
};

export default nextConfig;
