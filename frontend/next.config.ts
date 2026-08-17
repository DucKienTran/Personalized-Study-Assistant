import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    eslint: {
        ignoreDuringBuilds: true,
    },
    async rewrites() {
        return [
            {
                source: "/api/:path*",
                destination: "http://localhost:8000/api/:path*", 
            },
        ];
    },
    webpack(config) {
        config.resolve.alias.canvas = false;

        return config;
    },
};

export default nextConfig;
