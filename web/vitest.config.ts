import path from "node:path";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname),
      // server-only throws outside a React Server environment; tests run in
      // plain node, so stub it out (standard pattern for RSC-only modules).
      "server-only": path.resolve(__dirname, "lib/test/server-only-stub.ts"),
    },
  },
  test: {
    environment: "node",
    include: ["**/*.test.ts"],
  },
});
