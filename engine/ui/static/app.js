"use strict";

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.status);
  return r.json();
}

const MODES = {
  training: "Training - no clock, solutions shown, not scored",
  mastery: "Mastery - timed, domain-focussed, scored",
  exam: "Exam - full countdown, scored like the real thing",
};

let selectedBank = null;
let selectedMode = "mastery";
let selectedDomain = null;

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

async function loadBanks() {
  const banks = await api("/api/banks");
  const grid = document.getElementById("banks");
  grid.innerHTML = "";
  for (const b of banks) {
    const card = el("div", "card");
    card.appendChild(el("h3", null, b.title));
    const meta = el("div", "meta");
    meta.innerHTML = `<span>${b.n_questions} questions</span>` +
      `<span>draw ${b.draw_size}</span><span>${b.duration_minutes} min</span>` +
      `<span>pass ${Math.round(b.pass_threshold * 100)}%</span>`;
    card.appendChild(meta);
    card.onclick = () => openModal(b);
    grid.appendChild(card);
  }
}

function openModal(b) {
  selectedBank = b;
  selectedMode = "mastery";
  selectedDomain = null;
  document.getElementById("modal-title").textContent = b.title;
  const body = document.getElementById("modal-body");
  body.innerHTML = "";

  const m = el("div", "mode-row");
  for (const [id, label] of Object.entries({ training: "Training", mastery: "Mastery", exam: "Exam" })) {
    const btn = el("button", "btn" + (id === selectedMode ? " selected" : ""), label);
    btn.onclick = () => { selectedMode = id; document.querySelectorAll(".mode-row .btn").forEach(x => x.classList.remove("selected")); btn.classList.add("selected"); };
    m.appendChild(btn);
  }
  body.appendChild(el("p", "prompt", MODES[selectedMode]));
  body.appendChild(m);

  if (b.domains && Object.keys(b.domains).length > 1) {
    body.appendChild(el("p", null, "Focus domain (optional):"));
    const chips = el("div", "chips");
    const chip = el("span", "chip", "All");
    chip.onclick = () => { selectedDomain = null; document.querySelectorAll(".chip").forEach(x => x.classList.remove("selected")); chip.classList.add("selected"); };
    chip.classList.add("selected");
    chips.appendChild(chip);
    for (const d of Object.keys(b.domains)) {
      const c = el("span", "chip", d);
      c.onclick = () => { selectedDomain = d; document.querySelectorAll(".chip").forEach(x => x.classList.remove("selected")); c.classList.add("selected"); };
      chips.appendChild(c);
    }
    body.appendChild(chips);
  }
  document.getElementById("modal").classList.remove("hidden");
}

async function startAttempt() {
  const a = await api("/api/attempts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bank: selectedBank.id, mode: selectedMode, focus_domain: selectedDomain }),
  });
  window.location = `/exam.html?attempt=${a.id}`;
}

async function loadAttempts() {
  const attempts = await api("/api/attempts");
  const tbody = document.querySelector("#attempts-table tbody");
  tbody.innerHTML = "";
  for (const a of attempts) {
    const row = el("tr");
    row.appendChild(el("td", null, a.bank));
    row.appendChild(el("td", null, a.mode));
    row.appendChild(el("td", null, a.status));
    if (a.result) {
      const pct = Math.round(a.result.pct * 100);
      row.appendChild(el("td", null, pct + "%"));
      row.appendChild(el("td", a.result.passed ? "pass" : "fail", a.result.passed ? "PASS" : "FAIL"));
    } else {
      row.appendChild(el("td", null, "-"));
      row.appendChild(el("td", null, "-"));
    }
    tbody.appendChild(row);
  }
}

document.getElementById("modal-start").onclick = startAttempt;
document.getElementById("modal-cancel").onclick = () => document.getElementById("modal").classList.add("hidden");
loadBanks().catch(console.error);
loadAttempts().catch(console.error);
