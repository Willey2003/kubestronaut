"use strict";

const params = new URLSearchParams(window.location.search);
const ATTEMPT_ID = params.get("attempt");
let attempt = null;
let current = 0;

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.status);
  return r.json();
}

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

function fmt(secs) {
  if (secs < 0) return "untimed";
  const m = String(Math.floor(secs / 60)).padStart(2, "0");
  const s = String(secs % 60).padStart(2, "0");
  return `${m}:${s}`;
}

async function load() {
  attempt = await api(`/api/attempts/${ATTEMPT_ID}`);
  document.getElementById("mode").textContent = attempt.mode;
  document.getElementById("bank-title").textContent = `${attempt.bank} - ${attempt.questions.length} questions`;
  if (attempt.result) { renderResult(); return; }
  if (attempt.seconds_remaining === 0 && attempt.mode !== "training") { await submit(); return; }
  renderNav();
  showQuestion(current);
  if (attempt.mode !== "training") tick();
}

function renderNav() {
  const nav = document.getElementById("qlist");
  nav.innerHTML = "";
  attempt.questions.forEach((q, i) => {
    const btn = el("button", "q" + (i === 0 ? " active" : ""), `${i + 1}. ${q.title}`);
    btn.onclick = () => { current = i; showQuestion(i); };
    nav.appendChild(btn);
  });
}

function showQuestion(i) {
  current = i;
  const q = attempt.questions[i];
  document.querySelectorAll(".qlist .q").forEach((x, j) => {
    x.classList.toggle("active", j === i);
  });
  const panel = document.getElementById("qpanel");
  panel.innerHTML = "";
  panel.appendChild(el("h3", null, `Q${i + 1}: ${q.title}`));
  const meta = el("div", "meta", `${q.kind} / ${q.domain}`);
  panel.appendChild(meta);
  panel.appendChild(el("div", "prompt", q.prompt));

  if (q.kind === "knowledge") {
    const opts = el("div", "options");
    for (const [k, v] of Object.entries(q.options)) {
      const opt = el("div", "option", `(${k}) ` + v.replace(/\n/g, "\n    "));
      opt.onclick = () => saveAnswer(q.qid, k);
      if (attempt.mode === "training" && q.answer === k) opt.style.borderColor = "var(--good)";
      opts.appendChild(opt);
    }
    panel.appendChild(opts);
  } else {
    const note = el("div", "prompt", "Complete this task on your OpenShift cluster, then continue.");
    note.style.marginTop = "12px";
    panel.appendChild(note);
  }
  if (attempt.mode === "training") {
    const sol = el("div", "solution");
    if (q.kind === "knowledge") {
      sol.innerHTML = `<strong>Answer: ${q.answer}</strong><pre>${escapeHtml(q.explanation)}</pre>`;
    } else {
      sol.innerHTML = `<strong>Solution</strong><pre>${escapeHtml(q.solution)}</pre>`;
    }
    panel.appendChild(sol);
  }

  const navbtns = el("div", "nav-btns");
  const prev = el("button", "btn", "Previous");
  prev.onclick = () => { if (current > 0) showQuestion(current - 1); };
  const next = el("button", "btn primary", "Next");
  next.onclick = () => { if (current < attempt.questions.length - 1) showQuestion(current + 1); };
  if (current > 0) navbtns.appendChild(prev);
  if (current < attempt.questions.length - 1) navbtns.appendChild(next);
  panel.appendChild(navbtns);
}

async function saveAnswer(qid, value) {
  await api(`/api/attempts/${ATTEMPT_ID}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers: { [qid]: value } }),
  });
  const btns = document.querySelectorAll(".qlist .q");
  const idx = attempt.questions.findIndex(q => q.qid === qid);
  if (btns[idx]) btns[idx].classList.add("done");
}

function tick() {
  const t = document.getElementById("timer");
  const left = attempt.seconds_remaining;
  t.textContent = fmt(left);
  t.classList.toggle("low", left < 300);
  attempt.seconds_remaining -= 1;
  if (attempt.seconds_remaining < 0) submit();
  setTimeout(tick, 1000);
}

async function submit() {
  document.getElementById("submit").disabled = true;
  await api(`/api/attempts/${ATTEMPT_ID}/submit`, { method: "POST" });
  await load();
}

function renderResult() {
  document.querySelector(".exam-layout").classList.add("hidden");
  document.getElementById("submit").style.display = "none";
  const r = attempt.result;
  const pct = Math.round(r.pct * 100);
  const head = document.getElementById("result-head");
  head.textContent = r.passed ? "PASS" : "FAIL";
  head.style.color = r.passed ? "var(--good)" : "var(--bad)";
  document.getElementById("result-score").textContent =
    `Score ${pct}% (${r.earned}/${r.possible} pts) - threshold ${Math.round(r.threshold * 100)}%`;
  const domains = document.getElementById("result-domains");
  domains.innerHTML = "";
  for (const d of r.domains) {
    const wrap = el("div", "bar-wrap", `${d.domain} - ${Math.round(d.pct * 100)}%`);
    const bar = el("div", "bar");
    const fill = el("div", "fill");
    fill.style.width = `${Math.round(d.pct * 100)}%`;
    bar.appendChild(fill);
    wrap.appendChild(bar);
    domains.appendChild(wrap);
  }
  const detail = document.getElementById("result-detail");
  detail.innerHTML = "";
  r.results.forEach((q, i) => {
    const row = el("div", "check-row");
    const color = q.verdict === "pass" ? "var(--good)" : "var(--bad)";
    row.innerHTML = `<strong style="color:${color}">${q.verdict.toUpperCase()}</strong> ` +
      `${i + 1}. ${escapeHtml(q.title)} <span style="color:var(--muted)">(${q.earned}/${q.max})</span>`;
    for (const c of q.detail) {
      if (c.output !== undefined) {
        row.innerHTML += `<pre>${escapeHtml(c.desc)} -> ${c.pass ? "PASS" : "FAIL"}\n  out: ${escapeHtml(c.output)}</pre>`;
      }
    }
    detail.appendChild(row);
  });
  document.getElementById("result").classList.remove("hidden");
}

function escapeHtml(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

document.getElementById("submit").onclick = submit;
if (!ATTEMPT_ID) { document.body.innerHTML = "No attempt id."; } else { load().catch(console.error); }
