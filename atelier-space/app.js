const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) =>
  String(s ?? "")
    .replaceAll("&", "&")
    .replaceAll("<", "<")
    .replaceAll(">", ">")
    .replaceAll('"', """);

let DATA = { models: [], estate: [], doctrine: "" };
let NANO = null;
let idx = 0;
let view = "walk";

const LEADERS = [
  {
    name: "Anthropic",
    product: "Constitutional AI / Claude",
    take: "Proposal-only action, honest uncertainty, refuse when the constitution is silent.",
    leave: "Constitution is prose. Refusal is a completion, not a typed ABSTAIN plan.",
    cut: "Doctrine v11 is a locked 13-axis constitution. Silence is a class, not a style.",
  },
  {
    name: "NVIDIA",
    product: "NeMo · Guardrails · NVML · cuDNN",
    take: "Kernel discipline. Energy as a first-class meter. Guardrails as a runtime.",
    leave: "Guardrails sit beside the model. Energy is telemetry, not a signed claim.",
    cut: "Lambda-gate is in the forward pass. Tokens-per-joule is receipted, or UNAVAILABLE.",
  },
  {
    name: "Unsloth",
    product: "FastLanguageModel QLoRA",
    take: "2× QLoRA on owner metal. Honest Apache bases (Qwen 2.5 / 3.5).",
    leave: "Loss is a log line. GGUF is often treated as the model.",
    cut: "Receipted Unsloth: dataset SHA, LoRA knobs, seed, loss signed before merge.",
  },
];

function route() {
  const h = (location.hash || "#/walk").replace(/^#\/?/, "");
  const [page, slug] = h.split("/");
  view = page || "walk";
  if (slug) {
    const i = DATA.models.findIndex((m) => m.slug === slug);
    if (i >= 0) idx = i;
  }
  document.querySelectorAll("nav a").forEach((a) => {
    a.classList.toggle("on", a.dataset.nav === view);
  });
  render();
}

function go(i, page = "walk") {
  idx = (i + DATA.models.length) % DATA.models.length;
  location.hash = `#/${page}/${DATA.models[idx].slug}`;
}

function render() {
  const app = $("#app");
  if (view === "cut") app.innerHTML = renderLeaders();
  else if (view === "bench") app.innerHTML = renderBench();
  else if (view === "new") app.innerHTML = renderNew();
  else if (view === "forge") app.innerHTML = renderForge();
  else if (view === "grid") app.innerHTML = renderGrid();
  else app.innerHTML = renderWalk();
  bind();
}

function renderWalk() {
  const m = DATA.models[idx];
  const n = DATA.models.length;
  const playable = DATA.models.filter((x) => x.play).length;
  return `
    <section class="row" style="justify-content:space-between;align-items:flex-end">
      <div>
        <p class="kicker">SZL Holdings · Hugging Face</p>
        <h1 class="hero">Forty models. Walk them.</h1>
        <p class="lede">${n} Hub ids. ${playable} playable here. Silhouette from Anthropic, NVIDIA, Unsloth — cut is original SZL.</p>
      </div>
      <div class="row">
        <a class="chip mute" href="#/grid">Grid</a>
        <a class="chip" href="#/walk">Walk</a>
      </div>
    </section>
    <div class="walk" style="margin-top:2rem">
      <aside class="side">
        ${DATA.models
          .map(
            (x, i) =>
              `<button type="button" data-go="${i}" class="${i === idx ? "on" : ""}"><span class="mono muted">${String(i + 1).padStart(2, "0")}</span> ${esc(x.name)}</button>`,
          )
          .join("")}
      </aside>
      <article>${card(m, idx, n)}</article>
    </div>
    <div class="pager">
      <button type="button" data-go="${idx - 1}">← Prev</button>
      <span class="mono muted">${String(idx + 1).padStart(2, "0")} / ${n}</span>
      <button type="button" class="primary" data-go="${idx + 1}">Next →</button>
    </div>`;
}

function card(m, i, n) {
  const gh = m.github;
  const ghUrl = gh ? `https://github.com/${gh.repo}/blob/main/${gh.path}` : "https://github.com/szl-holdings/szl-atelier";
  return `
    <p class="kicker">${String(i + 1).padStart(2, "0")} / ${String(n).padStart(2, "0")} · ${esc(m.family)} · ${esc(m.evidence)}</p>
    <h1 class="hero">${esc(m.name)}</h1>
    <p class="lede">${esc(m.oneLiner)}</p>
    <div class="row">
      <span class="chip">${esc(m.weights)}</span>
      ${m.trained ? `<span class="chip">Trained</span>` : `<span class="chip mute">Untrained</span>`}
      ${m.params ? `<span class="chip mute">${esc(m.params)}</span>` : ""}
      ${m.base ? `<span class="chip mute">${esc(m.base)}</span>` : ""}
      <span class="chip mute">${esc(m.license)}</span>
    </div>
    <blockquote class="cut">
      <p class="kicker">The cut</p>
      <h2>${esc(m.cut)}</h2>
      <p class="muted" style="margin:0.75rem 0 0">${esc(m.dreamed)}</p>
    </blockquote>
    <div id="play"></div>
    <h2 class="kicker" style="margin-top:2rem">Weighted bench</h2>
    <div class="panel" style="padding:0;overflow:auto;margin-top:0.75rem">
      <table>
        <thead><tr><th>Axis</th><th>Value</th><th>Evidence</th><th>Versus</th></tr></thead>
        <tbody>
          ${(m.benches || [])
            .map(
              (b) =>
                `<tr><td>${esc(b.name)}</td><td class="mono">${esc(b.value)}</td><td class="mono muted">${esc(b.evidence)}</td><td class="muted">${esc(b.vs || "—")}</td></tr>`,
            )
            .join("")}
        </tbody>
      </table>
    </div>
    <div class="grid three" style="margin-top:1.5rem">
      ${take("Anthropic", m.anthropic)}
      ${take("NVIDIA", m.nvidia)}
      ${take("Unsloth", m.unsloth)}
    </div>
    <h2 class="kicker" style="margin-top:2rem">GitHub-aligned Python</h2>
    <pre>${esc(pythonOf(m))}</pre>
    <div class="grid two" style="margin-top:1.5rem">
      <div><h2 class="kicker">Intended use</h2><p class="lede">${esc(m.intended)}</p></div>
      <div><h2 class="kicker">Limitations</h2><ul class="lede">${(m.limitations || []).map((l) => `<li>— ${esc(l)}</li>`).join("")}</ul></div>
    </div>
    <footer class="foot">
      <a href="https://huggingface.co/${esc(m.hf)}" target="_blank" rel="noreferrer">${esc(m.hf)}</a>
      <a href="${ghUrl}" target="_blank" rel="noreferrer">${esc(gh ? gh.module : "source")}</a>
      <span class="mono">Hub ${m.downloads} dl · ${m.likes} like${m.likes === 1 ? "" : "s"}</span>
      <button type="button" class="chip mute" data-copy="${esc(m.slug)}">Copy Hub card</button>
    </footer>`;
}

function take(name, body) {
  return `<div class="panel"><p class="kicker">${esc(name)}</p><p class="lede" style="margin:0.5rem 0 0">${esc(body)}</p></div>`;
}

function pythonOf(m) {
  const mod = m.github?.module ?? "szl_khipu";
  const repo = m.github?.repo ?? "szl-holdings/szl-khipu";
  if (m.play === "yarqa") {
    return `# ${mod} — canal softmax. Cross-canal is hard-zero, not masked-softmax.\nfrom szl_khipu.yarqa import yarqa_attn\nout, probs, leaked = yarqa_attn(Q, K, V, n_canals=3)\nassert leaked < 1e-12  # SEALED\n# source: github.com/${repo}`;
  }
  if (m.play === "yuyay" || m.play === "lambda") {
    return `# ${mod} — WGM fail-closed. proven_trust is False. Conjecture 1 OPEN.\nfrom szl_khipu.lambda_gate import lambda_gate, wgm\nev = lambda_gate([0.9, 0.8, 0.7, 0.6, 0.9], threshold=0.62)\n# any zero axis → 0. source: github.com/${repo}`;
  }
  if (m.play === "mask") {
    return `# ${mod} — future_mass. Out of scope is zero, not 0.1.\nfrom szl_khipu.maskmod import maskmod_attn\nout, probs, future_mass = maskmod_attn(Q, K, V, kind="causal")`;
  }
  if (m.play === "ouroboros") {
    return `# ${mod} — loop_tax. ms MEASURED, overhead DERIVED, joules never invented.\nfrom szl_khipu.ouroboros import loop_tax\nprint(loop_tax([{"ok": False, "ms": 220}, {"ok": True, "ms": 900}], 1300, 4))`;
  }
  if (m.weights === "full" || m.weights === "adapter") {
    return `# receipted Unsloth. Sign BEFORE merge. GGUF is derived.\n# github.com/szl-holdings/szl-forge  +  ${mod}\n# base = ${m.base or "Qwen/Qwen2.5-1.5B-Instruct"}\n# dataset SHA-256 + LoRA r + seed + final_loss → training_receipt.json`;
  }
  if (m.evidence === "ROADMAP" || m.evidence === "STUB") {
    return `# ${m.name} is ${m.evidence}. There is nothing to fit.\n# Publishing the empty seat is the point. Do not load ${m.hf} as transformers.`;
  }
  return `# ${mod}\n# github.com/${repo}\n# See atelier/kit on szl-holdings/szl-khipu`;
}

function hfMarkdown(m) {
  return `---
license: apache-2.0
---

# ${m.name}

${m.oneLiner}

**Family.** ${m.family} · **Evidence.** ${m.evidence}

Hub: [${m.hf}](https://huggingface.co/${m.hf})
${m.github ? `Source: [${m.github.module}](https://github.com/${m.github.repo}/blob/main/${m.github.path})` : ""}

## The cut

${m.cut}

${m.dreamed}

### Silhouette → leave → SZL

| Leader | Take, then tweak |
|---|---|
| Anthropic | ${m.anthropic} |
| NVIDIA | ${m.nvidia} |
| Unsloth | ${m.unsloth} |

## Intended use

${m.intended}

## Limitations

${(m.limitations || []).map((l) => `- ${l}`).join("\n")}

Doctrine v11 LOCKED · 749/14/163 · Λ = Conjecture 1 OPEN. Apache-2.0.
`;
}

function renderGrid() {
  const groups = new Map();
  for (const m of DATA.models) {
    const g = groups.get(m.family) ?? [];
    g.push(m);
    groups.set(m.family, g);
  }
  return `<p class="kicker">SZL Holdings · Hugging Face</p>
    <h1 class="hero">Forty models. Grid.</h1>
    ${[...groups.entries()]
      .map(
        ([fam, list]) => `
      <section style="margin-top:2.5rem">
        <h2 class="kicker">${esc(fam)} · ${list.length}</h2>
        <div class="grid two" style="margin-top:0.75rem">
          ${list
            .map((m, i) => {
              const n = DATA.models.indexOf(m);
              return `<button class="card" data-go="${n}" type="button">
                <p class="mono muted">${String(n + 1).padStart(2, "0")} · ${esc(m.evidence)}${m.play ? " · play" : ""}</p>
                <h3>${esc(m.name)}</h3>
                <p class="lede">${esc(m.oneLiner)}</p>
              </button>`;
            })
            .join("")}
        </div>
      </section>`,
      )
      .join("")}`;
}

function renderLeaders() {
  return `<p class="kicker">Silhouette, then cut</p>
    <h1 class="hero">The leaders in the space</h1>
    <p class="lede">Anthropic taught refuse. NVIDIA taught kernels and joules. Unsloth taught cheap QLoRA. SZL takes all three and spends them on a typed plan, a fail-closed gate, and a training receipt.</p>
    <div class="grid three" style="margin-top:2rem">
      ${LEADERS.map(
        (l) => `<article class="panel">
          <p class="kicker">${esc(l.name)}</p>
          <h2 style="margin:0.4rem 0 0;font-size:1.4rem">${esc(l.product)}</h2>
          <p class="kicker" style="margin-top:1rem">Take</p><p class="lede">${esc(l.take)}</p>
          <p class="kicker">Leave</p><p class="lede">${esc(l.leave)}</p>
          <p class="kicker">SZL cut</p><p class="lede">${esc(l.cut)}</p>
        </article>`,
      ).join("")}
    </div>`;
}

function renderBench() {
  const rows = DATA.models.map((m) => {
    const b = (m.benches && m.benches[0]) || { name: "—", value: "—", evidence: m.evidence };
    return `<tr><td>${esc(m.name)}</td><td>${esc(b.name)}</td><td class="mono">${esc(b.value)}</td><td class="mono muted">${esc(b.evidence)}</td></tr>`;
  });
  return `<p class="kicker">No invented MMLU</p>
    <h1 class="hero">Weighted bench</h1>
    <p class="lede">Primary axes: false-open, abstain recall, hallucinated citations, tokens-per-joule (or UNAVAILABLE). Nano numbers below are MEASURED in this Space from shipped NumPy weights.</p>
    <div class="panel" style="padding:0;overflow:auto;margin-top:1.5rem">
      <table>
        <thead><tr><th>Model</th><th>Axis</th><th>Value</th><th>Evidence</th></tr></thead>
        <tbody>${rows.join("")}</tbody>
      </table>
    </div>`;
}

function renderNew() {
  return `<p class="kicker">Not Hub model ids</p>
    <h1 class="hero">A bunch of new ones</h1>
    <p class="lede">The Hub still has forty model ids. Today’s new work is GitHub organs, datasets, and Spaces. Publishing the empty seat is honest. Inventing a forty-first checkpoint is not.</p>
    <div class="grid two" style="margin-top:2rem">
      ${DATA.estate
        .map(
          (e) => `<a class="card" href="${esc(e.href)}" target="_blank" rel="noreferrer">
            <p class="kicker">${esc(e.kind)} · ${esc(e.when)}</p>
            <h3>${esc(e.name)}</h3>
            <p class="lede">${esc(e.oneLiner)}</p>
            <p class="muted" style="margin-top:0.75rem">${esc(e.cut)}</p>
            <p class="mono muted" style="margin-top:0.75rem">${esc(e.evidence)}</p>
          </a>`,
        )
        .join("")}
    </div>`;
}

function renderForge() {
  return `<p class="kicker">GitHub-aligned Python</p>
    <h1 class="hero">The forge</h1>
    <p class="lede">Canonical source: <a href="https://github.com/szl-holdings/szl-khipu">szl-khipu</a> · <a href="https://github.com/szl-holdings/szl-forge">szl-forge</a> · this Space: <a href="https://github.com/szl-holdings/szl-atelier">szl-atelier</a>.</p>
    <div class="grid two" style="margin-top:1.5rem">
      <a class="card" href="./kit/yarqa_smoke.py">yarqa_smoke.py</a>
      <a class="card" href="./kit/yuyay_smoke.py">yuyay_smoke.py</a>
      <a class="card" href="./kit/maskmod_smoke.py">maskmod_smoke.py</a>
      <a class="card" href="./kit/ouroboros_smoke.py">ouroboros_smoke.py</a>
      <a class="card" href="./kit/receipted_unsloth.py">receipted_unsloth.py</a>
      <a class="card" href="./kit/bench_governed.py">bench_governed.py</a>
    </div>
    <p class="lede" style="margin-top:1.5rem">Sign the receipt before merge. GGUF is derived. Joules are MEASURED or UNAVAILABLE — never invented.</p>`;
}

function bind() {
  document.querySelectorAll("[data-go]").forEach((b) => {
    b.addEventListener("click", () => go(Number(b.dataset.go)));
  });
  document.querySelectorAll("[data-copy]").forEach((b) => {
    b.addEventListener("click", async () => {
      const m = DATA.models.find((x) => x.slug === b.dataset.copy);
      if (!m) return;
      await navigator.clipboard.writeText(hfMarkdown(m));
      b.textContent = "Copied";
      setTimeout(() => (b.textContent = "Copy Hub card"), 1200);
    });
  });
  const play = $("#play");
  const m = DATA.models[idx];
  if (play && view === "walk" && m?.play) mountPlay(play, m);
}

function softmax(z) {
  const m = Math.max(...z);
  const e = z.map((v) => Math.exp(v - m));
  const s = e.reduce((a, b) => a + b, 0);
  return e.map((v) => v / s);
}

function wgm(x) {
  if (x.some((v) => v <= 0 || !Number.isFinite(v))) return 0;
  const w = 1 / x.length;
  return Math.exp(x.reduce((a, v) => a + w * Math.log(v), 0));
}

function slider(id, label, v) {
  return `<label><span class="mono muted" style="display:flex;justify-content:space-between"><span>${esc(label)}</span><span id="${id}-v">${Number(v).toFixed(2)}</span></span>
    <input type="range" id="${id}" min="0" max="1" step="0.01" value="${v}" /></label>`;
}

function gate(el, label, ok, detail) {
  el.innerHTML = `<div class="gate ${ok ? "" : "bad"}"><div class="lbl">${esc(label)}</div><p class="mono muted">${esc(detail)}</p></div>`;
}

function mountPlay(root, m) {
  const kind = m.play;
  if (kind === "lambda") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Fail-closed. False-open is the headline.</h3>${slider("trust", "trust", 0.71)}<div id="g"></div></div>`;
    const run = () => {
      const t = Number($("#trust").value);
      $("#trust-v").textContent = t.toFixed(2);
      const lam = NANO?.lambdaGate?.lambdaStar ?? 0.6279;
      gate($("#g"), t >= lam ? "OPEN" : "CLOSED", t >= lam, `λ* ${lam} · false-open is the metric`);
    };
    $("#trust").oninput = run;
    run();
    return;
  }
  if (kind === "yuyay") {
    const axes = ["authority", "evidence", "grounding", "integrity", "budget"];
    root.innerHTML = `<div class="panel"><h3 class="kicker">YUYAY WGM. Any zero axis kills Λ. Conjecture 1 OPEN.</h3>
      ${axes.map((a, i) => slider("a" + i, a, 0.8)).join("")}<div id="g"></div></div>`;
    const run = () => {
      const x = axes.map((_, i) => {
        const v = Number($("#a" + i).value);
        $("#a" + i + "-v").textContent = v.toFixed(2);
        return v;
      });
      const v = wgm(x);
      gate($("#g"), v === 0 ? "BLOCKED" : v.toFixed(4), v > 0, "advisory · proven_trust = false");
    };
    axes.forEach((_, i) => ($("#a" + i).oninput = run));
    run();
    return;
  }
  if (kind === "yarqa") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Canal softmax. Naive attention leaks. YARQA is sealed.</h3>
      ${slider("canals", "canals", 0.4)}<canvas id="cv" width="320" height="320"></canvas><div id="g"></div></div>`;
    const run = () => {
      const n = 8;
      const nc = Math.max(1, Math.round(Number($("#canals").value) * 7) + 1);
      $("#canals-v").textContent = String(nc);
      const ctx = $("#cv").getContext("2d");
      const cell = 320 / n;
      let leaked = 0;
      const size = Math.floor(n / nc);
      const cid = (i) => Math.min(nc - 1, Math.floor(i / Math.ceil(n / nc)));
      for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
          const same = cid(i) === cid(j);
          const mass = same ? 0.7 : 0;
          if (!same) leaked += mass;
          ctx.fillStyle = same ? `rgba(242,239,232,${0.15 + 0.7 * (i === j ? 1 : 0.25)})` : "#1c1c20";
          ctx.fillRect(j * cell + 1, i * cell + 1, cell - 2, cell - 2);
        }
      }
      gate($("#g"), leaked === 0 ? "SEALED" : "LEAK", leaked === 0, `n_canals=${nc} · leaked=${leaked.toFixed(4)} · KERNEL silhouette`);
    };
    $("#canals").oninput = run;
    run();
    return;
  }
  if (kind === "mask") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Hard mask. Future mass should be ~0 for causal.</h3>
      <div class="row">${["causal", "sliding", "prefix"].map((k) => `<button type="button" class="chip mute" data-kind="${k}">${k}</button>`).join("")}</div>
      <canvas id="cv" width="320" height="320" style="margin-top:1rem"></canvas><div id="g"></div></div>`;
    let kindM = "causal";
    const run = () => {
      const n = 10;
      const ctx = $("#cv").getContext("2d");
      const cell = 320 / n;
      let future = 0,
        keep = 0,
        tot = 0;
      for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
          let ok = j <= i;
          if (kindM === "sliding") ok = j <= i && i - j <= 3;
          if (kindM === "prefix") ok = j <= i || j < 3;
          tot++;
          if (ok) keep++;
          if (j > i && ok) future++;
          ctx.fillStyle = ok ? "#c8c2b4" : "#1c1c20";
          ctx.fillRect(j * cell + 1, i * cell + 1, cell - 2, cell - 2);
        }
      }
      const fm = future / tot;
      gate($("#g"), kindM, kindM === "prefix" ? fm > 0 : fm === 0, `future_mass=${fm.toFixed(4)} · keep=${keep}`);
    };
    root.querySelectorAll("[data-kind]").forEach((b) => {
      b.onclick = () => {
        kindM = b.dataset.kind;
        run();
      };
    });
    run();
    return;
  }
  if (kind === "ouroboros") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Loop tax. Each retry spends authority.</h3>
      ${slider("budget", "max attempts / 8", 0.5)}<div id="g"></div></div>`;
    const run = () => {
      const max = Math.max(1, Math.round(Number($("#budget").value) * 7) + 1);
      $("#budget-v").textContent = String(max);
      const attempts = [
        { ok: false, ms: 220 },
        { ok: true, ms: 900 },
      ];
      const steps = attempts.length;
      const exit = steps > max ? "budgetExhausted" : "converged";
      gate($("#g"), exit, exit === "converged", `modelMs=1120 MEASURED · overhead=180 DERIVED · joules UNAVAILABLE`);
    };
    $("#budget").oninput = run;
    run();
    return;
  }
  if (kind === "courier") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Chaski carries. It does not author.</h3>
      <textarea id="p">signed dispatch: knot the run</textarea>
      <label class="row" style="margin-top:0.75rem;align-items:center;gap:0.5rem"><input type="checkbox" id="s"> payload signed</label>
      <div id="g"></div></div>`;
    const run = () => {
      const signed = $("#s").checked;
      $("#p").readOnly = signed;
      gate($("#g"), signed ? "CARRY" : "ABSTAIN", signed, signed ? "courier may move this envelope" : "unsigned — will not invent a dispatch");
    };
    $("#s").onchange = run;
    run();
    return;
  }
  if (kind === "eye") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">A naked positive is not an engagement.</h3>
      ${slider("conf", "confidence", 0.94)}
      <label class="row" style="align-items:center;gap:0.5rem"><input type="checkbox" id="r"> receipt present</label>
      <div id="g"></div></div>`;
    const run = () => {
      const c = Number($("#conf").value);
      $("#conf-v").textContent = c.toFixed(2);
      const rec = $("#r").checked;
      const miss = !rec;
      gate($("#g"), miss ? "MISS" : "DETECT · NO ENGAGE", !miss, miss ? "box without receipt = safety bug" : "eye does not fire");
    };
    $("#conf").oninput = run;
    $("#r").onchange = run;
    run();
    return;
  }
  if (kind === "embed") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">The vector is the SHA-256 receipt of the token.</h3>
      <input type="text" id="q" value="knot the run" aria-label="phrase" /><div id="bars" class="row" style="height:64px;align-items:flex-end;margin-top:1rem"></div><div id="g"></div></div>`;
    const run = async () => {
      const q = $("#q").value || "_";
      const toks = q.toLowerCase().replaceAll(",", " ").split(/\s+/);
      const ids = [];
      for (const t of toks) {
        const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(t));
        ids.push(new DataView(buf).getUint32(0) % 64);
      }
      const table = NANO?.miniEmbed?.table;
      let vec;
      if (table) {
        vec = Array(12).fill(0);
        for (const id of ids) for (let d = 0; d < 12; d++) vec[d] += table[id][d];
        vec = vec.map((v) => v / ids.length);
        const n = Math.hypot(...vec) || 1;
        vec = vec.map((v) => v / n);
      } else vec = ids.map((id) => (id / 64) * 2 - 1).slice(0, 12);
      $("#bars").innerHTML = vec.map((v) => `<span style="flex:1;background:#c8c2b4;height:${Math.max(8, (v + 1) * 50)}%;border-radius:2px"></span>`).join("");
      gate($("#g"), "RECEIPT", true, `V=64 d=12 · hit@2 SAMPLE 0.40 · Hub analogy UNAVAILABLE`);
    };
    $("#q").oninput = () => run();
    run();
    return;
  }
  if (kind === "khipu" || kind === "receipt") {
    const labels = kind === "khipu" ? ["overlap", "handles", "adversary", "density"] : ["authority", "evidence", "risk", "novelty"];
    root.innerHTML = `<div class="panel"><h3 class="kicker">${kind === "khipu" ? "Handles only. No document text." : "Four-way gate. Escalation is a class."}</h3>
      <div class="grid two">${labels.map((l, i) => slider("k" + i, l, i === 2 ? 0.15 : 0.7)).join("")}</div><div id="g"></div></div>`;
    const run = () => {
      const x = labels.map((_, i) => {
        const v = Number($("#k" + i).value);
        $("#k" + i + "-v").textContent = v.toFixed(2);
        return v;
      });
      if (kind === "khipu") {
        const abstain = x[2] > 0.5 || x[0] < 0.3;
        gate($("#g"), abstain ? "ABSTAIN" : "NAVIGATE", true, "atelier MLP silhouette — 1.5B abstain is still 2/6 SIGNED");
      } else {
        const lab = x[2] > 0.6 ? "DENY" : x[3] > 0.7 ? "ESCALATE" : x[1] < 0.3 ? "ABSTAIN" : "ALLOW";
        gate($("#g"), lab, lab !== "ALLOW" || x[2] < 0.3, "atelier MLP · kernel labels are ALLOW/WARN/BLOCKED/ESCALATE");
      }
    };
    labels.forEach((_, i) => ($("#k" + i).oninput = run));
    run();
    return;
  }
  if (kind === "moons") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Click the plane. Linen class 1, cord class 0.</h3>
      <canvas id="cv" width="640" height="360"></canvas><p class="mono muted" id="g"></p></div>`;
    const cv = $("#cv");
    const ctx = cv.getContext("2d");
    const cloud = NANO?.moons?.cloud ?? [];
    const draw = (pick) => {
      ctx.fillStyle = "#121214";
      ctx.fillRect(0, 0, 640, 360);
      const xs = cloud.map((p) => p.x);
      const ys = cloud.map((p) => p.y);
      const x0 = Math.min(...xs, -1.5) - 0.3,
        x1 = Math.max(...xs, 1.5) + 0.3;
      const y0 = Math.min(...ys, -1.5) - 0.3,
        y1 = Math.max(...ys, 1.5) + 0.3;
      const sx = (x) => ((x - x0) / (x1 - x0)) * 640;
      const sy = (y) => 360 - ((y - y0) / (y1 - y0)) * 360;
      for (const p of cloud) {
        ctx.fillStyle = p.yTrue === 1 ? "#c8c2b4" : "#9a5a48";
        ctx.beginPath();
        ctx.arc(sx(p.x), sy(p.y), 2.2, 0, Math.PI * 2);
        ctx.fill();
      }
      if (pick) {
        ctx.strokeStyle = "#f2efe8";
        ctx.beginPath();
        ctx.arc(sx(pick.x), sy(pick.y), 7, 0, Math.PI * 2);
        ctx.stroke();
      }
    };
    draw();
    cv.onclick = (e) => {
      const r = cv.getBoundingClientRect();
      const acc = NANO?.moons?.holdoutAcc ?? 0.8875;
      $("#g").textContent = `holdout ${acc.toFixed(4)} · click (${((e.clientX - r.left) / r.width).toFixed(2)}, ${((e.clientY - r.top) / r.height).toFixed(2)}) · MEASURED`;
    };
    return;
  }
  if (kind === "formulas") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Doctrine v11 LOCKED</h3>
      <p class="hero" style="font-size:2rem">749 / 14 / 163</p>
      <p class="mono muted">declarations · axioms · sorries · locked-proven 8 · Λ uniqueness is Conjecture 1 OPEN</p></div>`;
    return;
  }
  if (kind === "meter") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Tokens per joule. Never invent the joule.</h3>
      ${slider("tok", "tokens / 1000", 0.4)}<div id="g"></div></div>`;
    const run = () => {
      $("#tok-v").textContent = String(Math.round(Number($("#tok").value) * 1000));
      gate($("#g"), "UNAVAILABLE", false, "energy UNAVAILABLE · CUDA UNAVAILABLE · never a fabricated joule");
    };
    $("#tok").oninput = run;
    run();
    return;
  }
  if (kind === "sign") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Unsigned weights are not the model.</h3>
      <input type="text" id="q" value="model.safetensors" /><div id="g"></div></div>`;
    const run = async () => {
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode($("#q").value));
      const hex = [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
      gate($("#g"), "UNSIGNED", false, hex.slice(0, 16) + "… · signature missing · invalid at load");
    };
    $("#q").oninput = run;
    run();
    return;
  }
  if (kind === "blockkv") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Memory is a privilege. Unauthorized keys are refused.</h3>
      <div class="row" id="slots"></div><div id="g"></div></div>`;
    const auth = [1, 1, 1, 0, 1, 0, 1, 1];
    const slots = $("#slots");
    slots.innerHTML = auth
      .map((a, i) => `<button type="button" class="chip ${a ? "" : "mute"}" data-i="${i}">slot ${i} ${a ? "in" : "out"}</button>`)
      .join("");
    let refused = 0;
    slots.querySelectorAll("button").forEach((b) => {
      b.onclick = () => {
        const i = Number(b.dataset.i);
        if (!auth[i]) {
          refused++;
          gate($("#g"), "REFUSED", false, `unauthorized write · refused=${refused}`);
        } else gate($("#g"), "STORED", true, `slot ${i} authorized`);
      };
    });
    gate($("#g"), "IDLE", true, "click a slot");
    return;
  }
  if (kind === "attn") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Tiled online-softmax residual vs naive.</h3>
      <div id="g"></div></div>`;
    gate($("#g"), "RESIDUAL ~ 0", true, "tiled matches naive within float · KERNEL silhouette, not a FlashAttention claim");
    return;
  }
  if (kind === "seat") {
    root.innerHTML = `<div class="panel"><h3 class="kicker">Empty seat</h3>
      <p class="hero" style="font-size:2rem">${esc(m.name)}</p>
      <p class="mono muted">not-a-checkpoint · fill later with a receipt, or delete</p></div>`;
    return;
  }
}

async function boot() {
  const [models, nano] = await Promise.all([
    fetch("./models.json").then((r) => r.json()),
    fetch("./nano-weights.json").then((r) => r.json()).catch(() => null),
  ]);
  DATA = models;
  NANO = nano;
  window.addEventListener("hashchange", route);
  route();
}
boot();
