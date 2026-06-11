import type { NextConfig } from "next";

// Em dev, o FastAPI roda separado (uvicorn na porta 8000) e o Next faz proxy.
// Na Vercel, o rewrite de vercel.json envia /api/py/* para a function Python.
const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    return [
      {
        source: "/api/py/:path*",
        destination: "http://127.0.0.1:8000/api/py/:path*",
      },
    ];
  },
};

export default nextConfig;
