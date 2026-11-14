// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

// CI passes the values from actions/configure-pages (origin + base_path),
// so custom domains and project pages both work. Local dev serves from "/".
const site = process.env.SITE_ORIGIN || "http://localhost:4321";
const base = process.env.SITE_BASE || "/";

export default defineConfig({
  site,
  base,
  trailingSlash: "always",
  build: { format: "directory" },
  // Chinese is the default and lives at the root; English under /en/.
  // Keep in sync with src/i18n/index.ts (LOCALES / DEFAULT_LOCALE).
  i18n: {
    locales: ["zh-CN", "en"],
    defaultLocale: "zh-CN",
    routing: { prefixDefaultLocale: false },
  },
  vite: { plugins: [tailwindcss()] },
});
