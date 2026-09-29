/*
 * A11oy Holo-Constellation v2.0.0
 * Deterministic route identity, accessible estate navigation, and low-cost
 * progressive visual enhancement. No fetch, tracking, storage, or cookies.
 * Palettes re-point at SZL Kanchay tokens; route identity and motifs are unchanged.
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

  // SZL Kanchay roles (kanchay/kanchay.css): ground, surface, text, paragraph,
  // gold accent, teal proof. Every surface shares them; its motif still varies.
  const KANCHAY_PALETTE = Object.freeze([
    "var(--color-a11oy-bg)",
    "var(--color-a11oy-surface)",
    "var(--color-a11oy-text)",
    "var(--color-a11oy-text-sub)",
    "var(--color-a11oy-gold)",
    "var(--color-ink-signal)",
  ]);

  const PALETTES = [KANCHAY_PALETTE];

  const CURATED = {
    a11oy: {
      label: "a11oy Command",
      motif: "command-constellation",
      palette: KANCHAY_PALETTE,
    },
    proof: {
      label: "a11oy Proof Network",
      motif: "evidence-vault",
      palette: KANCHAY_PALETTE,
    },
    lyte: {
      label: "Lyte",
      motif: "signal-aurora",
      palette: KANCHAY_PALETTE,
    },
    vessels: {
      label: "Vessels",
      motif: "bathymetric-radar",
      palette: KANCHAY_PALETTE,
    },
    terra: {
      label: "Terra",
      motif: "topographic-parcels",
      palette: KANCHAY_PALETTE,
    },
    aegis: {
      label: "Aegis",
      motif: "threat-lattice",
      palette: KANCHAY_PALETTE,
    },
    "prism-counsel": {
      label: "PRISM Counsel",
      motif: "case-facets",
      palette: KANCHAY_PALETTE,
    },
    "carlota-jo": {
      label: "Carlota Jo",
      motif: "editorial-orbit",
      palette: KANCHAY_PALETTE,
    },
    nexus: {
      label: "Nexus",
      motif: "connection-field",
      palette: KANCHAY_PALETTE,
    },
    factory: {
      label: "a11oy Factory",
      motif: "assembly-circuit",
      palette: KANCHAY_PALETTE,
    },
    ouroboros: {
      label: "Ouroboros",
      motif: "recursive-ring",
      palette: KANCHAY_PALETTE,
    },
    khipu: {
      label: "KHIPU",
      motif: "woven-proof",
      palette: KANCHAY_PALETTE,
    },
    killinchu: {
      label: "Killinchu",
      motif: "agent-swarm",
      palette: KANCHAY_PALETTE,
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
    return {"id":"szl-khipu","label":"Szl Khipu","motif":"woven-proof","palette":KANCHAY_PALETTE,"source":"space-specific"};
    const id = surfaceCandidate();
    const curated = CURATED[id];
    if (curated) return { id, ...curated, source: "curated" };

    const seed = fnv1a(id);
    const palette = PALETTES[seed % PALETTES.length];
    return {
      id,
      label: titleCase(id) || "a11oy Space",
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
      "aria-label": "Open the a11oy Command origin",
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
      "aria-label": "a11oy ecosystem",
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
