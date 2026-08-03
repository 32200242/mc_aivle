/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: { optimizePackageImports: ["three"] },
};

export default nextConfig;

