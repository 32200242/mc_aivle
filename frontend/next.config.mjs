/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Windows 개발 PC와 소형 배포 인스턴스에서도 페이지 수집 시 메모리가 튀지 않도록 제한합니다.
  experimental: { cpus: 2 },
  // `next dev -H 0.0.0.0`을 127.0.0.1/localhost에서 열 때
  // 개발용 JS 청크와 HMR 요청이 교차 출처로 판정되지 않게 허용합니다.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
