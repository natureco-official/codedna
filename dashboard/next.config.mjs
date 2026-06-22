/** @type {import('next').NextConfig} */
const nextConfig = {
  // API_URL ortam değişkenini istemci tarafına aç
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

export default nextConfig;
