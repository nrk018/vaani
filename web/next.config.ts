import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@paper-design/shaders-react", "@paper-design/shaders"],
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [{ source: "/backend/:path*", destination: `${api}/:path*` }];
  },
};

export default nextConfig;
