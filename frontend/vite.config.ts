/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The app always calls the RELATIVE path /api. In the container, nginx proxies
// /api to the backend, so no backend URL is ever baked into the JavaScript.
// For `npm run dev` on a laptop, set API_PROXY_TARGET to where the backend runs.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": process.env.API_PROXY_TARGET ?? "http://backend:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
  },
});
