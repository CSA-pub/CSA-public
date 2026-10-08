// Old Cloudflare Pages host -> canonical domain. Exact-host match so branch-preview
// hosts and the custom domain are never redirected; everything else falls through
// to the static assets (404.html, _headers, _redirects unchanged).
const OLD_HOST = "csa-public.pages.dev";
const NEW_HOST = "csa.dataengineered.io";

// Retired page -> its successor (a renamed or merged asset). Cloudflare Pages does not
// apply _redirects to requests a Function serves, and this middleware serves every
// request, so the redirects live here.
// BEGIN:redirects -- written by scripts/generate_seo_pages.py from scripts/redirects.json; edit that file, not this block
const REDIRECTS = {
  "/catalysts/eftilagimod-alpha": "/catalysts/eftilagimod-alfa",
  "/catalysts/lorlatanib": "/catalysts/lorlatinib",
  "/catalysts/rina": "/catalysts/rinatabart-sesutecan",
  "/catalysts/ritlecitinib-higher": "/catalysts/ritlecitinib",
  "/catalysts/ritlecitinib-lower": "/catalysts/ritlecitinib"
};
// END:redirects

// Catalyst, sponsor and directory pages were also published under these locale prefixes
// until 2026-10 and are English-only now (only the homepage and the 404 page are
// translated). A request for one that would 404 goes to its English page when that page
// exists, so the redirect stops by itself if a translation is published again.
// Slugs are [a-z0-9-] (scripts/generate_seo_pages.py slugify), so nothing else can match.
const LOCALE_PAGE = /^\/(?:es|de|fr|pt-br)\/(catalysts|sponsors)(?:\/([a-z0-9-]*?))?(?:\.html)?\/?$/;

// Repo-only files. Pages serves the whole repository root, so without this the
// translation catalogs, the build scripts, their config, the README and dotfiles
// would be downloadable from the site. They get the site's normal 404 instead
// (they stay in the GitHub repository).
const REPO_ONLY_PREFIXES = ["/locales/", "/scripts/", "/data/"];
const REPO_ONLY_FILES = new Set(["/i18n.config.json", "/readme.md", "/vercel.json", "/requirements.txt"]);

function decodePath(pathname) {
  try {
    return decodeURIComponent(pathname).replace(/\/{2,}/g, "/");
  } catch {
    return null; // malformed escapes never name a real page
  }
}

// Matched on the decoded, slash-collapsed, lower-cased path, because the asset
// server also answers /locales%2Fes.json and //locales/es.json.
function isRepoOnly(pathname) {
  let path = decodePath(pathname);
  if (path === null) return true;
  path = path.toLowerCase();
  if (REPO_ONLY_FILES.has(path)) return true;
  if (REPO_ONLY_PREFIXES.some((prefix) => path.startsWith(prefix))) return true;
  // dotfiles and dot-segments (.gitignore, .github/, ..), but keep /.well-known/ usable
  return path.split("/").some((seg) => seg.startsWith(".") && seg !== ".well-known");
}

// The successor of a retired page, also when it is asked for with .html, a trailing
// slash or a locale prefix (a translated copy of a retired page redirects straight to
// the English successor, in one hop).
function redirectTarget(pathname) {
  let path = decodePath(pathname);
  if (path === null) return null;
  path = path.toLowerCase().replace(/\.html$/, "");
  if (path.length > 1) path = path.replace(/\/$/, "");
  const english = path.replace(/^\/(?:es|de|fr|pt-br)(?=\/)/, "");
  return Object.prototype.hasOwnProperty.call(REDIRECTS, english) ? REDIRECTS[english] : null;
}

// /es/catalysts/x -> /catalysts/x, /fr/sponsors/ -> /sponsors/; null for anything else.
function englishTwin(pathname) {
  const path = decodePath(pathname);
  const m = path === null ? null : path.match(LOCALE_PAGE);
  if (!m) return null;
  return m[2] && m[2] !== "index" ? `/${m[1]}/${m[2]}` : `/${m[1]}/`;
}

// A day of browser caching: Response.redirect sends no Cache-Control, and browsers keep
// an uncached 301 indefinitely, which would outlive a redirect that lifts itself.
function redirect(url, pathname) {
  const to = new URL(url);
  to.pathname = pathname;
  return new Response(null, {
    status: 301,
    headers: { Location: to.toString(), "Cache-Control": "public, max-age=86400" },
  });
}

export async function onRequest({ request, env, next }) {
  const url = new URL(request.url);
  const target = redirectTarget(url.pathname);
  if (url.hostname === OLD_HOST) {
    url.hostname = NEW_HOST;
    return redirect(url, target || url.pathname);
  }
  if (isRepoOnly(url.pathname)) {
    // A path that cannot exist makes Pages answer with 404.html, as for any unknown URL.
    const missing = await env.ASSETS.fetch(new URL("/__not_found__", url).toString());
    return new Response(missing.body, { status: 404, headers: missing.headers });
  }
  if (target) return redirect(url, target);
  const response = await next();
  if (response.status === 404) {
    const english = englishTwin(url.pathname);
    if (english) {
      const page = await env.ASSETS.fetch(new URL(english, url).toString());
      if (page.body) await page.body.cancel();
      if (page.status === 200) return redirect(url, english);
    }
  }
  return response;
}
