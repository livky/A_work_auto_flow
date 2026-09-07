import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { execFileSync } from "node:child_process";
export default defineConfig({
  plugins: [
    react(),
    {
      name: "release-manifest",
      apply: "build",
      closeBundle() {
        // Watch builds and release builds use the same verified relative resources.
        execFileSync(process.execPath, ["scripts/manifest.mjs"], {
          stdio: "inherit",
        });
      },
    },
  ],
  base: "./",
  build: {
    outDir: "../ui/workbench-assets",
    assetsDir: "assets",
    emptyOutDir: true,
    target: "es2022",
    sourcemap: false,
    rollupOptions: { output: { manualChunks: { graph: ["cytoscape"] } } },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test-setup.ts"],
  },
});
