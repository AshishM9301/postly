/**
 * Run `build` or `dev` with `SKIP_ENV_VALIDATION` to skip env validation. This is especially useful
 * for Docker builds.
 */
import "./src/env.js";

const apiInternalUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

/** @type {import("next").NextConfig} */
const config = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiInternalUrl}/api/:path*`,
      },
    ];
  },
};

export default config;
