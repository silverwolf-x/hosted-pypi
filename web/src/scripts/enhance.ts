// Progressive enhancement shared by every page. Pages are fully static and usable
// without JS; this adds copy buttons, tabs, theme toggle, relative times and search.

import type { Dict } from "../i18n";

const $$ = <T extends Element = HTMLElement>(sel: string, root: ParentNode = document) =>
  Array.from(root.querySelectorAll<T>(sel) as NodeListOf<T>);

// ── i18n ─────────────────────────────────────────────────────────────────
// Locale comes from <html lang>; strings from the JSON block rendered by Base.astro
// (Dict["client"] in src/i18n/zh.ts).
const lang = document.documentElement.lang || "zh-CN";
const strings: Partial<Dict["client"]> = JSON.parse(document.getElementById("i18n-client")?.textContent || "{}");
const format = (key: keyof Dict["client"], vars: Record<string, string | number>) =>
  (strings[key] ?? "").replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? ""));

// Remember the explicit language choice. This is only a preference record — the
// site never auto-redirects (static pages, no flash); Chinese stays the default.
for (const a of $$<HTMLAnchorElement>("[data-lang-switch]")) {
  a.addEventListener("click", () => localStorage.setItem("lang", a.dataset.langSwitch!));
}

// ── Theme ────────────────────────────────────────────────────────────────
for (const btn of $$("[data-theme-toggle]")) {
  btn.addEventListener("click", () => {
    const dark = !document.documentElement.classList.contains("dark");
    const apply = () => {
      document.documentElement.classList.toggle("dark", dark);
      localStorage.setItem("theme", dark ? "dark" : "light");
    };
    if (document.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
      document.startViewTransition(apply);
    } else {
      apply();
    }
  });
}

// ── Copy to clipboard ────────────────────────────────────────────────────
document.addEventListener("click", async (e) => {
  const btn = (e.target as Element).closest<HTMLElement>("[data-copy]");
  if (!btn) return;
  try {
    await navigator.clipboard.writeText(btn.dataset.copy ?? "");
    btn.dataset.copied = "";
    setTimeout(() => delete btn.dataset.copied, 1600);
  } catch {
    /* clipboard blocked (insecure context); leave button unchanged */
  }
});

// ── Tabs (WAI-ARIA tabs pattern, remembers last choice) ─────────────────
const TAB_KEY = "install-tab";
for (const root of $$("[data-tabs]")) {
  const tabs = $$<HTMLButtonElement>("[role=tab]", root);
  const select = (id: string, focus = false) => {
    for (const t of tabs) {
      const on = t.dataset.tab === id;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      if (on && focus) t.focus();
    }
    for (const p of $$("[role=tabpanel]", root)) p.hidden = p.dataset.panel !== id;
  };
  const saved = localStorage.getItem(TAB_KEY);
  if (saved && tabs.some((t) => t.dataset.tab === saved)) select(saved);
  for (const [i, t] of tabs.entries()) {
    t.addEventListener("click", () => {
      select(t.dataset.tab!);
      localStorage.setItem(TAB_KEY, t.dataset.tab!);
    });
    t.addEventListener("keydown", (e) => {
      const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (d) select(tabs[(i + d + tabs.length) % tabs.length]!.dataset.tab!, true);
    });
  }
}

// ── Relative times ───────────────────────────────────────────────────────
const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31536e6], ["month", 2592e6], ["week", 6048e5], ["day", 864e5], ["hour", 36e5], ["minute", 6e4],
];
for (const el of $$<HTMLTimeElement>("time[data-relative]")) {
  const diff = new Date(el.dateTime).getTime() - Date.now();
  const [unit, ms] = UNITS.find(([, ms]) => Math.abs(diff) >= ms) ?? ["minute", 6e4];
  el.title = new Date(el.dateTime).toLocaleString(lang);
  el.textContent = rtf.format(Math.round(diff / ms), unit);
}

// ── Package search + platform filter (home page) ────────────────────────
const search = document.querySelector<HTMLInputElement>("[data-search]");
if (search) {
  const cards = $$("[data-pkg]");
  const counter = document.querySelector("[data-count]");
  const empty = document.querySelector<HTMLElement>("[data-empty]");
  const chips = $$<HTMLButtonElement>("[data-os-filter]");
  let os = "all";

  const apply = () => {
    const q = search.value.trim().toLowerCase();
    let shown = 0;
    for (const c of cards) {
      const ok = (!q || c.dataset.pkg!.includes(q)) && (os === "all" || c.dataset.os!.split(" ").includes(os));
      c.hidden = !ok;
      if (ok) shown++;
    }
    if (counter) counter.textContent = q || os !== "all" ? format("count", { shown, total: cards.length }) : String(cards.length);
    if (empty) empty.hidden = shown > 0;
    const params = new URLSearchParams(location.search);
    q ? params.set("q", q) : params.delete("q");
    history.replaceState(null, "", params.size ? `?${params}` : location.pathname);
  };

  for (const chip of chips) {
    chip.addEventListener("click", () => {
      os = chip.dataset.osFilter!;
      for (const c of chips) c.setAttribute("aria-pressed", String(c === chip));
      apply();
    });
  }
  search.value = new URLSearchParams(location.search).get("q") ?? "";
  search.addEventListener("input", apply);
  apply();

  document.addEventListener("keydown", (e) => {
    const typing = (e.target as Element).closest("input, textarea, [contenteditable]");
    if ((e.key === "/" && !typing) || (e.key === "k" && (e.metaKey || e.ctrlKey))) {
      e.preventDefault();
      search.focus();
      search.select();
    } else if (e.key === "Escape" && e.target === search) {
      search.value = "";
      apply();
      search.blur();
    }
  });
}
