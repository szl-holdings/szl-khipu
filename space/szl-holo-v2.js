/*
 * A11oy Holo-Constellation v2.0.0
 * Deterministic route identity, accessible estate navigation, and low-cost
 * progressive visual enhancement. No fetch, tracking, storage, or cookies.
 * Palettes re-point at SZL KANCHAY founder tokens; route identity and motifs are unchanged.
 * SPDX-License-Identifier: Apache-2.0
 */
(() => {
  "use strict";

  if (window.__SZL_HOLO_V2__) return;
  window.__SZL_HOLO_V2__ = true;

  const VERSION = "2.0.0";
  const PRODUCT = "https://a-11-oy.com";
  const PROOF = "https://a11oy.net";
  const REDUCE_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)");
  const FINE_POINTER = window.matchMedia("(pointer: fine)");
  const SAVE_DATA = Boolean(navigator.connection && navigator.connection.saveData);

  // SZL KANCHAY founder roles (szl/szl-design-system.css): ground, surface, text,
  // paragraph, silver linework, silver shadow. Coral stays the one node in the mark;
  // every surface shares these roles and its motif still varies.
  const FOUNDER_PALETTE = Object.freeze([
    "var(--bg)",
    "var(--surface)",
    "var(--text)",
    "var(--text-sub)",
    "var(--color-silver-300)",
    "var(--color-silver-500)",
  ]);

  const PALETTES = [FOUNDER_PALETTE];

  const CURATED = {
    a11oy: {
      label: "A11oy Command",
      motif: "command-constellation",
      palette: FOUNDER_PALETTE,
    },
    proof: {
      label: "A11oy Proof Network",
      motif: "evidence-vault",
      palette: FOUNDER_PALETTE,
    },
    lyte: {
      label: "Lyte",
      motif: "signal-aurora",
      palette: FOUNDER_PALETTE,
    },
    vessels: {
      label: "Vessels",
      motif: "bathymetric-radar",
      palette: FOUNDER_PALETTE,
    },
    terra: {
      label: "Terra",
      motif: "topographic-parcels",
      palette: FOUNDER_PALETTE,
    },
    aegis: {
      label: "Aegis",
      motif: "threat-lattice",
      palette: FOUNDER_PALETTE,
    },
    "prism-counsel": {
      label: "PRISM Counsel",
      motif: "case-facets",
      palette: FOUNDER_PALETTE,
    },
    "carlota-jo": {
      label: "Carlota Jo",
      motif: "editorial-orbit",
      palette: FOUNDER_PALETTE,
    },
    nexus: {
      label: "Nexus",
      motif: "connection-field",
      palette: FOUNDER_PALETTE,
    },
    factory: {
      label: "A11oy Factory",
      motif: "assembly-circuit",
      palette: FOUNDER_PALETTE,
    },
    ouroboros: {
      label: "Ouroboros",
      motif: "recursive-ring",
      palette: FOUNDER_PALETTE,
    },
    khipu: {
      label: "KHIPU",
      motif: "woven-proof",
      palette: FOUNDER_PALETTE,
    },
    killinchu: {
      label: "Killinchu",
      motif: "agent-swarm",
      palette: FOUNDER_PALETTE,
    },
  };

  const ROUTE_HINTS = [
    ["prism-counsel", ["prism-counsel", "prism counsel", "/counsel", "/legal"]],
    ["carlota-jo", ["carlota-jo", "carlota jo", "/advisory"]],
    ["ouroboros", ["ouroboros", "/research", "/thesis"]],
    ["killinchu", ["killinchu", "/agents", "agent forge", "agent swarm"]],
    ["factory", ["a11oy-factory", "szl-factory", "/factory", "/forge", "artifact factory"]],
    ["vessels", ["vessels", "/maritime", "fleet command", "voyage"]],
    ["terra", ["terra", "/real-estate", "real estate", "parcel"]],
    ["aegis", ["aegis", "/security", "/defense", "threat"]],
    ["lyte", ["lyte", "/observability", "business observability", "signal"]],
    ["nexus", ["nexus", "/integration", "connection fabric"]],
    ["khipu", ["khipu", "/kernel", "woven proof"]],
  ];

  const MOTIFS = [
    "command-constellation",
    "signal-aurora",
    "bathymetric-radar",
    "topographic-parcels",
    "threat-lattice",
    "case-facets",
    "editorial-orbit",
    "connection-field",
    "assembly-circuit",
    "recursive-ring",
    "woven-proof",
    "agent-swarm",
  ];

  const LINKS = [
    ["Command", `${PRODUCT}/`],
    ["Products", `${PRODUCT}/console`],
    ["Proof", `${PROOF}/record/`],
    ["Source", "https://github.com/szl-holdings"],
    ["Spaces", "https://huggingface.co/SZLHOLDINGS"],
  ];

  function slug(value) {
    return String(value || "")
      .normalize("NFKD")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 96);
  }

  function fnv1a(value) {
    let result = 0x811c9dc5;
    for (const character of String(value || "a11oy")) {
      result ^= character.charCodeAt(0);
      result = Math.imul(result, 0x01000193) >>> 0;
    }
    return result >>> 0;
  }

  function titleCase(value) {
    return String(value || "")
      .split("-")
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function huggingFaceSlug(host) {
    const match = host.match(/^(?:szlholdings|szl-holdings)-(.+)\.hf\.space$/i);
    return match ? slug(match[1]) : "";
  }

  function surfaceCandidate() {
    const host = location.hostname.toLowerCase();
    if (host === "a11oy.net" || host === "www.a11oy.net") return "proof";
    if (host === "a-11-oy.com" || host === "www.a-11-oy.com") {
      const path = location.pathname.toLowerCase();
      for (const [surface, hints] of ROUTE_HINTS) {
        if (hints.some((hint) => path.includes(hint.replace(" ", "-")))) return surface;
      }
      return "a11oy";
    }

    const hf = huggingFaceSlug(host);
    const path = location.pathname.toLowerCase();
    const title = document.title.toLowerCase();
    const bodyIdentity = `${document.body?.id || ""} ${document.body?.className || ""}`.toLowerCase();
    const haystack = `${host} ${hf} ${path} ${title} ${bodyIdentity}`;

    for (const [surface, hints] of ROUTE_HINTS) {
      if (hints.some((hint) => haystack.includes(hint))) return surface;
    }
    if (hf) return hf;
    return slug(path.split("/").filter(Boolean)[0]) || slug(host) || "a11oy";
  }

  function resolveTheme() {
    return {"id":"szl-khipu","label":"Szl Khipu","motif":"woven-proof","palette":FOUNDER_PALETTE,"source":"space-specific"};
    const id = surfaceCandidate();
    const curated = CURATED[id];
    if (curated) return { id, ...curated, source: "curated" };

    const seed = fnv1a(id);
    const palette = PALETTES[seed % PALETTES.length];
    return {
      id,
      label: titleCase(id) || "A11oy Space",
      motif: MOTIFS[(seed >>> 8) % MOTIFS.length],
      palette,
      source: "deterministic",
    };
  }

  function applyTheme(theme) {
    const [background, surface, foreground, muted, accent, accent2] = theme.palette;
    const root = document.documentElement;
    root.dataset.szlHolo = "v2";
    root.dataset.szlHoloSurface = theme.id;
    root.dataset.szlHoloMotif = theme.motif;
    root.dataset.szlHoloThemeSource = theme.source;
    root.style.setProperty("--szl-holo-bg", background);
    root.style.setProperty("--szl-holo-bg-deep", background);
    root.style.setProperty("--szl-holo-surface", surface);
    root.style.setProperty("--szl-holo-surface-2", surface);
    root.style.setProperty("--szl-holo-ink", foreground);
    root.style.setProperty("--szl-holo-muted", muted);
    root.style.setProperty("--szl-holo-accent", accent);
    root.style.setProperty("--szl-holo-accent-2", accent2);
  }

  function createElement(name, attributes = {}, text = null) {
    const node = document.createElement(name);
    for (const [key, value] of Object.entries(attributes)) {
      if (key === "className") node.className = value;
      else if (key === "dataset") Object.assign(node.dataset, value);
      else node.setAttribute(key, value);
    }
    if (text !== null) node.textContent = text;
    return node;
  }

  function addSkipLink() {
    if (document.querySelector(".szl-holo-skip, [data-szl-holo-skip]")) return;
    const main = document.querySelector("main, [role='main']");
    if (!main) return;
    if (!main.id) main.id = "szl-holo-main";
    const link = createElement("a", {
      className: "szl-holo-skip",
      href: `#${main.id}`,
      dataset: { szlHoloSkip: "true" },
    }, "Skip to main content");
    document.body.prepend(link);
  }

  function currentLink(href) {
    const target = new URL(href);
    const host = location.hostname.replace(/^www\./, "");
    if (target.hostname.replace(/^www\./, "") !== host) return false;
    if (target.pathname === "/") return location.pathname === "/";
    return location.pathname.startsWith(target.pathname.replace(/\/$/, ""));
  }

  function buildRail(theme) {
    if (document.querySelector(".szl-holo-rail") || document.documentElement.hasAttribute("data-szl-holo-no-rail")) return;

    const rail = createElement("header", {
      className: "szl-holo-rail",
      dataset: { szlHoloRail: "v2" },
    });
    const identity = createElement("a", {
      className: "szl-holo-identity",
      href: `${PRODUCT}/`,
      "aria-label": "Open the A11oy Command origin",
    });
    identity.append(createElement("span", { className: "szl-holo-mark", "aria-hidden": "true" }));
    const copy = createElement("span", { className: "szl-holo-copy" });
    copy.append(createElement("span", { className: "szl-holo-eyebrow" }, "SZL · Holo-Constellation"));
    copy.append(createElement("span", { className: "szl-holo-label" }, theme.label));
    identity.append(copy);

    const controls = createElement("div", { className: "szl-holo-controls" });
    const menu = createElement("button", {
      className: "szl-holo-menu",
      type: "button",
      "aria-label": "Open ecosystem navigation",
      "aria-expanded": "false",
      "aria-controls": "szl-holo-nav",
    }, "Menu");
    const nav = createElement("nav", {
      className: "szl-holo-nav",
      id: "szl-holo-nav",
      "aria-label": "A11oy ecosystem",
      dataset: { open: "false" },
    });
    for (const [label, href] of LINKS) {
      const attributes = { className: "szl-holo-link", href };
      if (currentLink(href)) attributes["aria-current"] = "page";
      nav.append(createElement("a", attributes, label));
    }
    controls.append(menu, nav);
    rail.append(identity, controls);
    document.body.prepend(rail);

    const close = ({ focus = false } = {}) => {
      nav.dataset.open = "false";
      menu.setAttribute("aria-expanded", "false");
      menu.setAttribute("aria-label", "Open ecosystem navigation");
      menu.textContent = "Menu";
      if (focus) menu.focus();
    };

    menu.addEventListener("click", () => {
      const open = nav.dataset.open !== "true";
      nav.dataset.open = String(open);
      menu.setAttribute("aria-expanded", String(open));
      menu.setAttribute("aria-label", open ? "Close ecosystem navigation" : "Open ecosystem navigation");
      menu.textContent = open ? "Close" : "Menu";
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && nav.dataset.open === "true") close({ focus: true });
    });
    document.addEventListener("pointerdown", (event) => {
      if (nav.dataset.open === "true" && !rail.contains(event.target)) close();
    });
  }

  function addAmbient() {
    if (document.getElementById("szl-holo-ambient")) return;
    const ambient = createElement("div", {
      id: "szl-holo-ambient",
      "aria-hidden": "true",
      dataset: { szlHoloDecorative: "true" },
    });
    document.body.prepend(ambient);
  }

  function addProgress() {
    if (document.querySelector(".szl-holo-progress")) return;
    document.body.append(createElement("div", {
      className: "szl-holo-progress",
      "aria-hidden": "true",
      dataset: { szlHoloDecorative: "true" },
    }));
  }

  function enhancePanels() {
    if (document.documentElement.hasAttribute("data-szl-holo-no-auto-panels")) return;
    const selectors = [
      "main .card",
      "main .panel",
      "main .metric-card",
      "main .feature-card",
      "main [class*='glass-card']",
      "main [class*='holo-card']",
      "main [data-panel]",
    ];
    const seen = new Set();
    for (const node of document.querySelectorAll(selectors.join(","))) {
      if (seen.size >= 24) break;
      if (seen.has(node) || node.closest("nav, header, footer, table, pre, code, form, dialog")) continue;
      seen.add(node);
      node.setAttribute("data-szl-holo-panel", "auto");
    }
  }

  function installMotion() {
    const root = document.documentElement;
    let pointerFrame = 0;
    let scrollFrame = 0;
    let lastX = window.innerWidth / 2;
    let lastY = Math.min(window.innerHeight * 0.22, 240);

    const commitPointer = () => {
      pointerFrame = 0;
      root.style.setProperty("--szl-holo-pointer-x", `${Math.round((lastX / Math.max(window.innerWidth, 1)) * 1000) / 10}%`);
      root.style.setProperty("--szl-holo-pointer-y", `${Math.round((lastY / Math.max(window.innerHeight, 1)) * 1000) / 10}%`);
    };

    const pointer = (event) => {
      if (REDUCE_MOTION.matches || !FINE_POINTER.matches || SAVE_DATA || document.hidden) return;
      lastX = event.clientX;
      lastY = event.clientY;
      if (!pointerFrame) pointerFrame = requestAnimationFrame(commitPointer);
    };

    const commitScroll = () => {
      scrollFrame = 0;
      const maximum = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const percentage = Math.max(0, Math.min(100, (window.scrollY / maximum) * 100));
      root.style.setProperty("--szl-holo-scroll", percentage.toFixed(2));
    };

    const scroll = () => {
      if (!scrollFrame) scrollFrame = requestAnimationFrame(commitScroll);
    };

    if (!SAVE_DATA) window.addEventListener("pointermove", pointer, { passive: true });
    window.addEventListener("scroll", scroll, { passive: true });
    window.addEventListener("resize", scroll, { passive: true });
    document.addEventListener("visibilitychange", () => {
      root.dataset.szlHoloPaused = String(document.hidden);
      if (!document.hidden) scroll();
    });
    REDUCE_MOTION.addEventListener?.("change", () => {
      root.dataset.szlHoloReducedMotion = String(REDUCE_MOTION.matches);
    });
    root.dataset.szlHoloReducedMotion = String(REDUCE_MOTION.matches);
    root.dataset.szlHoloSaveData = String(SAVE_DATA);
    commitPointer();
    commitScroll();
  }

  function boot() {
    if (!document.body || document.documentElement.hasAttribute("data-szl-holo-disabled")) return;
    const theme = resolveTheme();
    applyTheme(theme);
    addAmbient();
    addProgress();
    addSkipLink();
    buildRail(theme);
    enhancePanels();
    installMotion();

    window.SZLHolo = Object.freeze({
      version: VERSION,
      theme: Object.freeze({ ...theme, palette: [...theme.palette] }),
      resolveTheme,
      fnv1a,
      decorativeMotion: true,
      measuredTelemetry: false,
    });
    document.dispatchEvent(new CustomEvent("szl:holo-ready", {
      detail: { version: VERSION, surface: theme.id, motif: theme.motif, source: theme.source },
    }));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();

/*
 * SZL Public Experience v3.1
 * Viewport-, zoom-, and audience-aware adaptation for Holographic Space Fabric v2.
 * No network, analytics, cookies, storage, or product-state mutation.
 * SPDX-License-Identifier: Apache-2.0
 */
(function () {
  "use strict";

  if (window.__SZL_PUBLIC_EXPERIENCE_V3__) return;
  window.__SZL_PUBLIC_EXPERIENCE_V3__ = true;

  var VERSION = "3.1.0";
  var ROOT = document.documentElement;
  var raf = 0;
  var observer = null;
  var rootStyleObserver = null;
  var stopObserverTimer = 0;
  var lastViewportState = "";

  function layoutViewportWidth() {
    var visual = window.visualViewport && window.visualViewport.width;
    return Math.max(
      1,
      Math.round(Number(visual) || 0),
      Math.round(Number(window.innerWidth) || 0),
      Math.round(Number(ROOT.clientWidth) || 0)
    );
  }

  function layoutViewportHeight() {
    var visual = window.visualViewport && window.visualViewport.height;
    return Math.max(
      1,
      Math.round(Number(visual) || 0),
      Math.round(Number(window.innerHeight) || 0),
      Math.round(Number(ROOT.clientHeight) || 0)
    );
  }

  function cssZoom() {
    var value = 1;
    try {
      value = Number.parseFloat(window.getComputedStyle(ROOT).zoom || ROOT.style.zoom || "1");
    } catch (_error) {
      value = Number.parseFloat(ROOT.style.zoom || "1");
    }
    return Number.isFinite(value) && value > 0 ? value : 1;
  }

  function zoomTier(value) {
    if (value >= 3) return "extreme";
    if (value >= 1.5) return "high";
    return "normal";
  }

  function tier(width) {
    if (width < 480) return "phone";
    if (width < 768) return "compact";
    if (width < 1024) return "tablet";
    if (width < 1440) return "desktop";
    if (width < 1920) return "wide";
    if (width < 2560) return "theatre";
    return "ultrawide";
  }

  function orientation(width, height) {
    return width >= height ? "landscape" : "portrait";
  }

  function audience() {
    var value = "";
    try {
      value = new URLSearchParams(window.location.search || "").get("view") || "";
    } catch (_error) {}
    value = String(value).toLowerCase();
    if (value === "developer" || value === "dev" || value === "build") return "developer";
    if (value === "investor" || value === "diligence") return "investor";
    if (value === "operator" || value === "command") return "operator";
    return "user";
  }

  function humanize(value) {
    return String(value || "")
      .replace(/^szlholdings[-/]/i, "")
      .replace(/^szl-holdings[-/]/i, "")
      .replace(/[_-]+/g, " ")
      .replace(/\b\w/g, function (character) { return character.toUpperCase(); })
      .trim();
  }

  function declaredIdentity() {
    var meta = document.querySelector('meta[name="szl-space-slug"]');
    var value = ROOT.dataset.szlSpaceLabel || ROOT.dataset.szlSpaceSlug ||
      (meta && meta.getAttribute("content")) || "";
    if (!value) {
      var match = String(window.location.hostname || "").match(/^(?:szlholdings|szl-holdings)-(.+?)(?:\.static)?\.hf\.space$/i);
      value = match ? match[1] : "";
    }
    return humanize(value) || "SZL Holdings";
  }

  function ensureDocumentTitle() {
    if (String(document.title || "").trim()) return;
    document.title = declaredIdentity() + " · SZL Holdings";
  }

  function syncBars(currentZoomTier) {
    document.querySelectorAll("szl-space-ecosystem-bar").forEach(function (bar) {
      bar.dataset.szlZoomTier = currentZoomTier;
    });
  }

  function snapshot() {
    var width = layoutViewportWidth();
    var height = layoutViewportHeight();
    var zoom = cssZoom();
    return Object.freeze({
      version: VERSION,
      width: width,
      height: height,
      effectiveWidth: Math.max(280, Math.round(width / zoom)),
      zoom: zoom,
      zoomTier: zoomTier(zoom),
      viewportTier: tier(Math.max(280, Math.round(width / zoom))),
      orientation: orientation(width, height),
      audience: audience()
    });
  }

  function applyViewportState() {
    raf = 0;
    var state = snapshot();
    var key = [state.width, state.height, state.zoom.toFixed(3), state.audience].join("|");
    syncBars(state.zoomTier);
    ensureDocumentTitle();
    if (key === lastViewportState) return;
    lastViewportState = key;

    ROOT.dataset.szlSpaceHoloV2 = "true";
    ROOT.dataset.szlPublicExperienceV3 = "true";
    ROOT.dataset.szlViewportTier = state.viewportTier;
    ROOT.dataset.szlViewportOrientation = state.orientation;
    ROOT.dataset.szlZoomTier = state.zoomTier;
    ROOT.dataset.szlAudience = state.audience;
    ROOT.style.setProperty("--szl-viewport-width", state.width + "px");
    ROOT.style.setProperty("--szl-viewport-height", state.height + "px");
    ROOT.style.setProperty("--szl-effective-inline-size", state.effectiveWidth + "px");
    ROOT.style.setProperty("--szl-page-zoom", state.zoom.toFixed(3));
  }

  function scheduleViewportState() {
    if (raf) return;
    raf = window.requestAnimationFrame(applyViewportState);
  }

  function responsiveBarStyle() {
    return [
      ":host{position:sticky!important;top:0!important;inline-size:100%!important;max-inline-size:100%!important;z-index:2147483000!important}",
      ":host([data-szl-zoom-tier=high]),:host([data-szl-zoom-tier=extreme]){position:relative!important;top:auto!important}",
      ".bar{min-height:56px!important;padding-block:8px!important;padding-inline:max(clamp(12px,2.3vw,30px),env(safe-area-inset-left,0px)) max(clamp(12px,2.3vw,30px),env(safe-area-inset-right,0px))!important}",
      "nav a,button{min-width:54px!important;min-height:48px!important;border-radius:10px!important;touch-action:manipulation!important}",
      "nav{max-width:100%!important}",
      "@media(max-width:700px){.bar{position:relative!important;grid-template-columns:minmax(0,1fr) auto!important;gap:8px!important}.identity{min-width:0!important}.label{max-width:min(58vw,360px)!important}.eyebrow{font-size:8px!important}button{display:inline-flex!important}nav{position:absolute!important;top:calc(100% + 7px)!important;right:max(8px,env(safe-area-inset-right,0px))!important;left:max(8px,env(safe-area-inset-left,0px))!important;max-height:min(56dvh,420px)!important;max-width:calc(100vw - 16px)!important;overflow:auto!important;overscroll-behavior:contain!important;padding:8px!important;border-radius:14px!important}nav a{justify-content:flex-start!important;padding-inline:14px!important}}",
      "@media(max-width:420px){.bar{min-height:54px!important;padding-block:5px!important}.copy{gap:0!important}.label{font-size:12px!important}.mark{width:22px!important;height:22px!important}nav{top:calc(100% + 5px)!important}}",
      "@media(min-width:1440px){.bar{min-height:60px!important;padding-inline:max(40px,env(safe-area-inset-left,0px)) max(40px,env(safe-area-inset-right,0px))!important}nav a{padding-inline:14px!important}}",
      "@media(min-width:1920px){.bar{min-height:64px!important;padding-inline:max(64px,env(safe-area-inset-left,0px)) max(64px,env(safe-area-inset-right,0px))!important}.label{font-size:14px!important}nav{gap:8px!important}nav a{min-height:48px!important;padding-inline:18px!important;font-size:12px!important}}",
      "@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important;animation:none!important}}",
      "@media(forced-colors:active){.bar,nav,nav a,button{forced-color-adjust:auto!important}}"
    ].join("");
  }

  function enhanceBar(bar) {
    if (!bar || !bar.shadowRoot || bar.dataset.szlResponsiveV3 === "true") return;
    var style = document.createElement("style");
    style.dataset.szlResponsiveV3 = "true";
    style.textContent = responsiveBarStyle();
    bar.shadowRoot.appendChild(style);
    bar.dataset.szlResponsiveV3 = "true";
    bar.dataset.szlZoomTier = ROOT.dataset.szlZoomTier || zoomTier(cssZoom());

    var nav = bar.shadowRoot.querySelector("nav");
    var button = bar.shadowRoot.querySelector("button");
    if (button) button.setAttribute("title", "Open SZL product, proof, source, and Space navigation");
    if (nav) {
      nav.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", function () {
          nav.dataset.open = "false";
          if (button) {
            button.setAttribute("aria-expanded", "false");
            button.textContent = "Menu";
          }
        });
      });
    }
  }

  function enhanceBars() {
    document.querySelectorAll("szl-space-ecosystem-bar").forEach(enhanceBar);
  }

  function startBarObserver() {
    enhanceBars();
    if (!window.MutationObserver || observer) return;
    observer = new MutationObserver(function (records) {
      records.forEach(function (record) {
        record.addedNodes.forEach(function (node) {
          if (!node || node.nodeType !== 1) return;
          if (node.matches && node.matches("szl-space-ecosystem-bar")) enhanceBar(node);
          if (node.querySelectorAll) node.querySelectorAll("szl-space-ecosystem-bar").forEach(enhanceBar);
        });
      });
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    stopObserverTimer = window.setTimeout(function () {
      if (observer) observer.disconnect();
      observer = null;
      stopObserverTimer = 0;
    }, 30000);
  }

  function startRootStyleObserver() {
    if (!window.MutationObserver || rootStyleObserver) return;
    rootStyleObserver = new MutationObserver(scheduleViewportState);
    rootStyleObserver.observe(ROOT, { attributes: true, attributeFilter: ["style"] });
  }

  function initialize() {
    applyViewportState();
    startRootStyleObserver();
    startBarObserver();
    if (window.customElements && customElements.whenDefined) {
      customElements.whenDefined("szl-space-ecosystem-bar").then(enhanceBars).catch(function () {});
    }
  }

  Object.defineProperty(window, "SZLPublicExperience", {
    configurable: false,
    enumerable: false,
    writable: false,
    value: Object.freeze({ version: VERSION, snapshot: snapshot })
  });

  window.addEventListener("resize", scheduleViewportState, { passive: true });
  window.addEventListener("orientationchange", scheduleViewportState, { passive: true });
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", scheduleViewportState, { passive: true });
    window.visualViewport.addEventListener("scroll", scheduleViewportState, { passive: true });
  }
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) scheduleViewportState();
  });
  window.addEventListener("pagehide", function () {
    if (observer) observer.disconnect();
    if (rootStyleObserver) rootStyleObserver.disconnect();
    if (stopObserverTimer) window.clearTimeout(stopObserverTimer);
    if (raf) window.cancelAnimationFrame(raf);
  }, { once: true });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
}());
