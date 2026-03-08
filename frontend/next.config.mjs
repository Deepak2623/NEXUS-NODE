/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    // turbo: {},
  },
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${
          process.env.BACKEND_URL ?? "http://127.0.0.1:8000"
        }/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
