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
  vite: { plugins: [tailwindcss()] },
});
