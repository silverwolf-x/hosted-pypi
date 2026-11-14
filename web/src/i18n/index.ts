import { getAbsoluteLocaleUrl, getRelativeLocaleUrl } from "astro:i18n";
import en from "./en";
import zh from "./zh";

// Keep in sync with `i18n.locales` / `i18n.defaultLocale` in astro.config.mjs.
export const LOCALES = ["zh-CN", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "zh-CN";

export type Dict = typeof zh;

const DICTS: Record<Locale, Dict> = { "zh-CN": zh, en };

export function isLocale(value: unknown): value is Locale {
  return LOCALES.includes(value as Locale);
}

/** Normalize `Astro.currentLocale` (or any string) to a supported locale. */
export function toLocale(value: string | undefined): Locale {
  return isLocale(value) ? value : DEFAULT_LOCALE;
}

export function useTranslations(locale: Locale): Dict {
  return DICTS[locale];
}

/**
 * `params.locale` for `src/pages/[...locale]/` routes: the default locale has no
 * URL prefix (`prefixDefaultLocale: false`), other locales use their code.
 */
export function localeParam(locale: Locale): string | undefined {
  return locale === DEFAULT_LOCALE ? undefined : locale;
}

/** Page URL in a locale, including the site base, e.g. `/hosted-pypi/en/packages/x/`. */
export function localeUrl(locale: Locale, path = ""): string {
  return getRelativeLocaleUrl(locale, path);
}

export function absoluteLocaleUrl(locale: Locale, path = ""): string {
  return getAbsoluteLocaleUrl(locale, path);
}

/**
 * Strip the site base and locale prefix from a pathname, so the result can be
 * passed to `localeUrl()` for any locale: `/hosted-pypi/en/packages/x/` → `packages/x/`.
 */
export function pathWithinLocale(pathname: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/?$/, "/");
  let path = pathname.startsWith(base) ? pathname.slice(base.length) : pathname.replace(/^\//, "");
  for (const l of LOCALES) {
    if (l === DEFAULT_LOCALE) continue;
    if (path === l || path.startsWith(`${l}/`)) {
      path = path.slice(l.length + 1);
      break;
    }
  }
  return path;
}

/** Localized number / size / date formatting. */
export function formatNumber(locale: Locale, n: number): string {
  return new Intl.NumberFormat(locale).format(n);
}

export function formatBytes(locale: Locale, bytes: number): string {
  const units = ["byte", "kilobyte", "megabyte", "gigabyte"] as const;
  let n = bytes;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return new Intl.NumberFormat(locale, {
    style: "unit",
    unit: units[i]!,
    unitDisplay: "short",
    maximumFractionDigits: i === 0 || n >= 10 ? 0 : 1,
  }).format(n);
}

export function formatDate(locale: Locale, iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(locale, { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
}
