/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // turbo: {},
  },
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `${
          process.env.BACKEND_URL ?? 'http://localhost:8000'
        }/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
