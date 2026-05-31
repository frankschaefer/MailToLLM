"use strict";

/* ============================================================
   WalkFit – Geh-Rechner zum Abnehmen
   Reine Frontend-Logik, keine Abhängigkeiten.
   ============================================================ */

const LB_PER_KG = 2.2046226218;
const KCAL_PER_KG_FAT = 7700;      // ~ Energiegehalt von 1 kg Körperfett
const HEALTHY_MAX_KG_PER_WEEK = 0.75;

// Level-Profile: Tempo, MET-Wert, Standard-Dauer & Trainingstage
const LEVELS = {
  beginner:     { speed: 4.0, met: 3.0, minutes: 30, days: 5, label: "Anfänger",
                  hint: "Anfänger: gemütliches Tempo (~4 km/h), kürzere Einheiten, 5 Tage/Woche." },
  intermediate: { speed: 5.5, met: 4.3, minutes: 45, days: 6, label: "Mittel",
                  hint: "Mittel: zügiges Tempo (~5,5 km/h), 45 Min, 6 Tage/Woche." },
  advanced:     { speed: 6.5, met: 5.0, minutes: 60, days: 6, label: "Profi",
                  hint: "Profi: sportliches Power-Walking (~6,5 km/h), 60 Min, 6 Tage/Woche." },
};

const DAY_NAMES = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

const $ = (sel) => document.querySelector(sel);

let unit = "metric";

/* ---------- Einheiten-Umschaltung ---------- */
function getWeightKg(value) { return unit === "metric" ? value : value / LB_PER_KG; }
function toDisplayWeight(kg) { return unit === "metric" ? kg : kg * LB_PER_KG; }

function getHeightCm() {
  if (unit === "metric") return parseFloat($("#heightCm").value);
  const ft = parseFloat($("#heightFt").value) || 0;
  const inch = parseFloat($("#heightIn").value) || 0;
  return (ft * 12 + inch) * 2.54;
}

function switchUnit(next) {
  if (next === unit) return;

  const weightEl = $("#weight");
  const goalEl = $("#goal");

  // aktuelle Werte in kg merken
  const wKg = getWeightKg(parseFloat(weightEl.value));
  const gKg = getWeightKg(parseFloat(goalEl.value));
  const hCm = getHeightCm();

  unit = next;

  // UI-Sichtbarkeit
  document.querySelectorAll(".metric-only").forEach((e) => e.classList.toggle("hidden", unit !== "metric"));
  document.querySelectorAll(".imperial-only").forEach((e) => e.classList.toggle("hidden", unit !== "imperial"));
  document.querySelectorAll(".unit-weight").forEach((e) => (e.textContent = unit === "metric" ? "kg" : "lbs"));
  document.querySelectorAll(".unit-btn").forEach((b) => b.classList.toggle("active", b.dataset.unit === unit));

  // Gewichtswerte konvertieren
  const round = (n) => Math.round(n * 2) / 2;
  weightEl.value = round(toDisplayWeight(wKg));
  goalEl.value = round(toDisplayWeight(gKg));

  // Höhe konvertieren
  if (unit === "imperial") {
    const totalIn = hCm / 2.54;
    $("#heightFt").value = Math.floor(totalIn / 12);
    $("#heightIn").value = Math.round(totalIn % 12);
  } else {
    $("#heightCm").value = Math.round(hCm);
  }

  // Slider-Ranges anpassen
  configureWeightSliders();
  syncSlidersFromInputs();
}

function configureWeightSliders() {
  const wr = $("#weightRange"), gr = $("#goalRange");
  if (unit === "metric") {
    [wr, gr].forEach((s) => { s.min = 40; s.max = 200; s.step = 0.5; });
  } else {
    [wr, gr].forEach((s) => { s.min = 90; s.max = 440; s.step = 1; });
  }
}

/* ---------- Slider <-> Input Sync ---------- */
function link(inputId, rangeId) {
  const input = $("#" + inputId);
  const range = $("#" + rangeId);
  input.addEventListener("input", () => { range.value = input.value; });
  range.addEventListener("input", () => { input.value = range.value; });
}
function syncSlidersFromInputs() {
  $("#weightRange").value = $("#weight").value;
  $("#ageRange").value = $("#age").value;
  $("#goalRange").value = $("#goal").value;
}

/* ---------- Formatierung ---------- */
const fmt = (n, d = 0) => new Intl.NumberFormat("de-DE", { maximumFractionDigits: d, minimumFractionDigits: d }).format(n);

function formatWeeks(weeks) {
  if (weeks < 1) return "< 1 Woche";
  if (weeks < 8) return `${Math.round(weeks)} Wochen`;
  const months = weeks / 4.345;
  if (months < 12) return `${fmt(months, 1)} Monate`;
  return `${fmt(months / 12, 1)} Jahre`;
}

function formatDuration(min) {
  if (min < 60) return `${Math.round(min)} Min`;
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  return m ? `${h} h ${m} Min` : `${h} h`;
}

/* ---------- Kernberechnung ---------- */
function calculate() {
  const heightCm = getHeightCm();
  const weightKg = getWeightKg(parseFloat($("#weight").value));
  const goalKg = getWeightKg(parseFloat($("#goal").value));
  const age = parseInt($("#age").value, 10);
  const sex = document.querySelector('input[name="sex"]:checked').value;
  const levelKey = document.querySelector('input[name="level"]:checked').value;
  const lvl = LEVELS[levelKey];

  // Validierung
  if (!heightCm || heightCm < 100) return showError("Bitte gib eine gültige Größe ein.");
  if (!weightKg || weightKg < 30) return showError("Bitte gib ein gültiges Gewicht ein.");
  if (!goalKg || goalKg < 30) return showError("Bitte gib ein gültiges Zielgewicht ein.");

  const loseKg = weightKg - goalKg;

  // BMI
  const hM = heightCm / 100;
  const bmiNow = weightKg / (hM * hM);
  const bmiGoal = goalKg / (hM * hM);

  // Geh-Werte
  const minutes = lvl.minutes;
  const days = lvl.days;
  const speed = lvl.speed; // km/h

  // Kalorienverbrauch pro Tag durchs Gehen: MET * 3.5 * kg / 200  (kcal/min)
  const kcalPerMin = (lvl.met * 3.5 * weightKg) / 200;
  const kcalPerDay = kcalPerMin * minutes;

  // Strecke & Schritte
  const distanceKm = speed * (minutes / 60);
  const strideFactor = sex === "male" ? 0.415 : 0.413;
  const strideM = heightCm * strideFactor / 100;
  const stepsPerDay = (distanceKm * 1000) / strideM;

  // Wöchentliches Defizit nur durchs Gehen
  const weeklyDeficit = kcalPerDay * days;
  let kgPerWeek = weeklyDeficit / KCAL_PER_KG_FAT;

  // auf gesundes Maximum deckeln
  const capped = kgPerWeek > HEALTHY_MAX_KG_PER_WEEK;
  if (capped) kgPerWeek = HEALTHY_MAX_KG_PER_WEEK;

  const weeks = loseKg > 0 ? loseKg / kgPerWeek : 0;

  render({
    levelKey, lvl, sex, age,
    weightKg, goalKg, loseKg,
    bmiNow, bmiGoal,
    minutes, days, distanceKm, stepsPerDay,
    kcalPerDay, weeks, kgPerWeek, capped,
  });
}

/* ---------- Ausgabe ---------- */
function showError(msg) {
  const result = $("#result");
  result.classList.remove("hidden");
  $("#resultSummary").innerHTML = `⚠️ ${msg}`;
  $("#bmiNow").textContent = "–";
  $("#bmiGoal").textContent = "–";
  ["rLoss","rWeeks","rSteps","rTime","rDist","rKcal"].forEach((id) => ($("#" + id).textContent = "–"));
  $("#weekGrid").innerHTML = "";
  $("#milestoneList").innerHTML = "";
  result.scrollIntoView({ behavior: "smooth", block: "start" });
}

function render(r) {
  const result = $("#result");
  result.classList.remove("hidden");

  const wUnit = unit === "metric" ? "kg" : "lbs";
  const lossDisplay = toDisplayWeight(r.loseKg);

  // Zusammenfassung
  if (r.loseKg <= 0) {
    $("#resultSummary").innerHTML =
      `🎉 Dein Zielgewicht liegt auf oder über deinem aktuellen Gewicht – du musst nicht abnehmen!
       Nutze das Gehen, um deine Fitness zu halten.`;
  } else {
    $("#resultSummary").innerHTML =
      `Um <strong>${fmt(lossDisplay, 1)} ${wUnit}</strong> abzunehmen, geh als
       <strong>${r.lvl.label}</strong> ca. <strong>${formatDuration(r.minutes)}</strong> an
       <strong>${r.days} Tagen/Woche</strong>. Geschätzte Dauer:
       <strong>${formatWeeks(r.weeks)}</strong>.` +
      (r.capped ? ` <em>(auf ein gesundes Tempo von max. ${fmt(HEALTHY_MAX_KG_PER_WEEK,2)} kg/Woche begrenzt)</em>` : "");
  }

  // BMI
  $("#bmiNow").textContent = fmt(r.bmiNow, 1);
  $("#bmiGoal").textContent = fmt(r.bmiGoal, 1);
  // Marker-Position: BMI 15..40 auf 0..100% mappen
  const pos = Math.max(0, Math.min(100, ((r.bmiNow - 15) / (40 - 15)) * 100));
  $("#bmiMarker").style.left = pos + "%";

  // Stats
  $("#rLoss").textContent = r.loseKg > 0 ? `${fmt(lossDisplay, 1)} ${wUnit}` : "0";
  $("#rWeeks").textContent = r.loseKg > 0 ? formatWeeks(r.weeks) : "–";
  $("#rSteps").textContent = fmt(r.stepsPerDay, 0);
  $("#rTime").textContent = formatDuration(r.minutes);
  $("#rDist").textContent = `${fmt(unit === "metric" ? r.distanceKm : r.distanceKm * 0.621371, 1)} ${unit === "metric" ? "km" : "mi"}`;
  $("#rKcal").textContent = `${fmt(r.kcalPerDay, 0)} kcal`;

  // Wochenplan
  renderWeek(r);

  // Etappenziele
  renderMilestones(r);

  result.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderWeek(r) {
  const grid = $("#weekGrid");
  grid.innerHTML = "";
  // Trainingstage über die Woche verteilen
  const trainPattern = {
    5: [1, 1, 1, 0, 1, 1, 0], // Mo-Mi, Fr, Sa
    6: [1, 1, 1, 1, 1, 1, 0],
    7: [1, 1, 1, 1, 1, 1, 1],
  }[r.days] || [1, 1, 1, 1, 1, 0, 0];

  DAY_NAMES.forEach((name, i) => {
    const active = trainPattern[i];
    const div = document.createElement("div");
    div.className = "day" + (active ? "" : " rest");
    div.innerHTML = active
      ? `<div class="day-name">${name}</div><div class="day-min">${r.minutes}<small>Minuten</small></div>`
      : `<div class="day-name">${name}</div><div class="day-min">Pause<small>&nbsp;</small></div>`;
    grid.appendChild(div);
  });
}

function renderMilestones(r) {
  const ul = $("#milestoneList");
  ul.innerHTML = "";
  if (r.loseKg <= 0) return;

  const wUnit = unit === "metric" ? "kg" : "lbs";
  const fractions = [0.25, 0.5, 0.75, 1.0];
  fractions.forEach((f) => {
    const lostKg = r.loseKg * f;
    const atWeek = r.weeks * f;
    const remainingKg = r.weightKg - lostKg;
    const li = document.createElement("li");
    li.innerHTML =
      `<span class="ms-dot"></span>
       <span class="ms-week">${formatWeeks(atWeek)}</span>
       <span class="ms-text">${f === 1 ? "🏁 Ziel erreicht: " : "–"} ${fmt(toDisplayWeight(lostKg), 1)} ${wUnit} weg
       → ${fmt(toDisplayWeight(remainingKg), 1)} ${wUnit}</span>`;
    ul.appendChild(li);
  });
}

/* ---------- Level-Hinweis ---------- */
function updateLevelHint() {
  const key = document.querySelector('input[name="level"]:checked').value;
  $("#levelHint").textContent = LEVELS[key].hint;
}

/* ---------- Init ---------- */
function init() {
  link("weight", "weightRange");
  link("age", "ageRange");
  link("goal", "goalRange");
  configureWeightSliders();
  syncSlidersFromInputs();

  document.querySelectorAll(".unit-btn").forEach((b) =>
    b.addEventListener("click", () => switchUnit(b.dataset.unit))
  );
  document.querySelectorAll('input[name="level"]').forEach((r) =>
    r.addEventListener("change", updateLevelHint)
  );
  updateLevelHint();

  $("#walkForm").addEventListener("submit", (e) => {
    e.preventDefault();
    calculate();
  });
}

document.addEventListener("DOMContentLoaded", init);
