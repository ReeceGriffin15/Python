import { api } from "./api.js";
import { renderWeeklyChart } from "./chart.js";
import { copy } from "./copy.js";

// ---------------------------------------------------------------- tiny DOM helper

function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "class") el.className = v;
    else if (k in el && typeof v !== "string") el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) el.append(c);
  return el;
}

const fmtDate = (iso, opts = { weekday: "long", day: "numeric", month: "long" }) =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-GB", opts);
const errText = (e) => copy.errors[e.code] || copy.errors.generic;

// ---------------------------------------------------------------- state & routing

const state = {
  view: "today",
  easier: false,
  options: null,      // overrides today's options when "easier" is on
  selected: null,     // challenge id chosen in the morning
  eveningFor: null,   // log id whose evening form is open
  result: null,       // last outcome response, shown once
  error: null,
};

const viewEl = document.getElementById("view");
const views = { today: renderToday, progress: renderProgress, you: renderYou };

function go(view) {
  state.view = view;
  state.error = null;
  renderNav();
  render();
}

async function render() {
  try {
    await views[state.view]();
  } catch (e) {
    viewEl.replaceChildren(h("p", { class: "error" }, errText(e)));
  }
}

async function act(fn) {
  try {
    state.error = null;
    await fn();
  } catch (e) {
    state.error = errText(e);
  }
  render();
}

function renderNav() {
  document.getElementById("nav").replaceChildren(
    ...Object.keys(views).map((v) =>
      h("button", { "aria-current": state.view === v ? "page" : undefined, onclick: () => go(v) }, copy.nav[v]),
    ),
  );
}

// ---------------------------------------------------------------- shared bits

function slider(name, value, label, hint) {
  const out = h("output", {}, String(value));
  const input = h("input", {
    type: "range", min: 0, max: 100, step: 5, value, name, "aria-label": label,
    oninput: (e) => (out.textContent = e.target.value),
  });
  return h("div", {},
    h("label", {}, label, hint ? h("div", { class: "hint" }, hint) : null),
    h("div", { class: "slider" }, input, out),
  );
}

function challengeBody(c) {
  return [
    h("div", {},
      h("span", { class: "chip" }, copy.categories[c.category]),
      h("span", { class: "chip" }, copy.suds.target(c.suds_target)),
    ),
    h("div", { class: "text" }, c.text),
    h("p", { class: "kv" }, h("b", {}, copy.today.drop + ": "), c.safety_trap_to_drop),
    h("p", { class: "kv" }, h("b", {}, copy.today.success + ": "), c.success_criterion),
  ];
}

function seg(name, options, initial, onChange) {
  const wrap = h("div", { class: "seg", role: "group" });
  let value = initial;
  const buttons = options.map(([v, label]) =>
    h("button", {
      type: "button", "aria-pressed": String(v === value),
      onclick: () => {
        value = v;
        buttons.forEach((b, i) => b.setAttribute("aria-pressed", String(options[i][0] === v)));
        onChange?.(v);
      },
    }, label),
  );
  wrap.append(...buttons);
  wrap.value = () => value;
  return wrap;
}

function errorBox() {
  return state.error ? h("p", { class: "error", role: "alert" }, state.error) : null;
}

// ---------------------------------------------------------------- TODAY

async function renderToday() {
  const t = await api.today();
  document.getElementById("date").textContent = fmtDate(t.date);
  const nodes = [statusStrip(t)];

  if (t.days_since_last >= 3 && !t.entry) nodes.push(h("div", { class: "card soft" }, copy.today.welcomeBack));

  for (const p of t.pending) {
    nodes.push(h("div", { class: "card warn" },
      h("div", { class: "row" },
        h("span", {}, copy.today.pendingTitle(fmtDate(p.date, { weekday: "long" }))),
        h("button", { class: "link", onclick: () => { state.eveningFor = p.id; render(); } }, copy.today.logIt),
      ),
      state.eveningFor === p.id ? eveningForm(p) : null,
    ));
  }

  nodes.push(h("h2", {}, copy.today.heading));
  if (state.result) nodes.push(resultCard(state.result));
  else if (!t.entry) nodes.push(...morning(t));
  else if (!t.entry.is_logged) nodes.push(planCard(t.entry));
  else nodes.push(loggedCard(t.entry));

  if (!t.frozen_today && t.freezes_left > 0 && !(t.entry && t.entry.is_logged && t.entry.completion !== "none")) {
    nodes.push(h("div", { class: "row" },
      h("button", { class: "link", onclick: () => act(() => api.freeze()) }, copy.today.freezeBtn),
      h("span", { class: "muted small" }, copy.week.freezesLeft(t.freezes_left)),
    ));
  }
  if (t.frozen_today) nodes.push(h("p", { class: "muted" }, copy.today.frozen));
  nodes.push(errorBox());
  viewEl.replaceChildren(...nodes.filter(Boolean));
}

function statusStrip(t) {
  const { tier, week } = t;
  const tierSub = tier.is_max ? copy.tierMax : copy.tierProgress(Math.min(tier.full_at_current, tier.needed), tier.needed, tier.current + 1);
  return h("div", { class: "status" },
    h("div", { class: "card" },
      h("div", { class: "label" }, "Tier"),
      h("div", { class: "value" }, copy.tierLabel(tier.current)),
      tier.is_max ? null : h("div", { class: "pips", "aria-label": tierSub, title: tierSub },
        ...Array.from({ length: tier.needed }, (_, i) => h("span", { class: `pip ${i < tier.full_at_current ? "on" : ""}` }))),
      tier.unlocked > tier.current ? h("div", { class: "note" }, copy.tierHigherUnlocked(tier.unlocked)) : null,
    ),
    h("div", { class: "card" },
      h("div", { class: "label" }, "Week"),
      h("div", { class: "value" }, copy.week.score(week.score, week.target)),
      h("div", { class: "pips", "aria-hidden": "true" },
        ...Array.from({ length: week.target }, (_, i) => h("span", { class: `pip ${i < week.score ? "on" : ""}` }))),
    ),
  );
}

function morning(t) {
  const options = state.easier && state.options ? state.options : t.options;
  const selected = options.find((c) => c.id === state.selected);
  const nodes = [h("p", { class: "muted" }, copy.today.pickPrompt)];

  for (const c of options) {
    nodes.push(h("button", {
      class: "card challenge", type: "button", "aria-pressed": String(c.id === state.selected),
      onclick: () => { state.selected = c.id; render(); },
    }, ...challengeBody(c)));
  }

  if (t.easier_tier) {
    nodes.push(h("button", {
      class: "link",
      onclick: () => act(async () => {
        state.easier = !state.easier;
        state.selected = null;
        state.options = state.easier ? await api.options(true) : null;
      }),
    }, state.easier ? copy.today.normalToggle : copy.today.easierToggle(t.easier_tier)));
  }

  if (selected) nodes.push(ifThenForm(selected));
  return nodes;
}

function ifThenForm(c) {
  const when = h("input", { type: "text", name: "when", required: true, maxlength: 200, placeholder: copy.today.whenPlaceholder });
  const where = h("input", { type: "text", name: "where", required: true, maxlength: 200, placeholder: copy.today.wherePlaceholder });
  const feared = h("input", { type: "text", name: "feared", maxlength: 500, placeholder: copy.today.fearedPlaceholder });
  const predicted = slider("predicted", c.suds_target, copy.today.predicted, copy.suds.scale);
  const form = h("form", {
    class: "card",
    onsubmit: (e) => {
      e.preventDefault();
      act(async () => {
        await api.pick({
          challenge_id: c.id,
          plan_when: when.value,
          plan_where: where.value,
          predicted_suds: Number(form.elements.predicted.value),
          feared_outcome: feared.value || null,
        });
        Object.assign(state, { selected: null, easier: false, options: null });
      });
    },
  },
    h("h3", { style: "margin-top:0" }, copy.today.ifThenTitle),
    h("label", {}, copy.today.when), when,
    h("label", {}, copy.today.where), where,
    h("label", {}, copy.today.then),
    h("p", { class: "kv" }, c.text),
    predicted,
    h("label", {}, copy.today.feared), feared,
    h("button", { class: "btn block", type: "submit" }, copy.today.commit),
  );
  return form;
}

function planCard(entry) {
  const c = entry.challenge;
  return h("div", { class: "card" },
    h("p", { class: "muted", style: "margin-top:0" }, copy.today.planLine(entry.plan_when, entry.plan_where)),
    ...challengeBody(c),
    entry.predicted_suds !== null ? h("p", { class: "kv" }, copy.today.predictedWas(entry.predicted_suds)) : null,
    entry.feared_outcome ? h("p", { class: "kv" }, copy.today.fearWas(entry.feared_outcome)) : null,
    state.eveningFor === entry.id
      ? eveningForm(entry)
      : h("div", { class: "row", style: "margin-top:12px" },
          h("button", { class: "btn", onclick: () => { state.eveningFor = entry.id; render(); } }, copy.today.logIt),
          h("button", { class: "link", onclick: () => act(() => api.unpick(entry.id)) }, copy.today.changePick),
        ),
  );
}

function eveningForm(entry) {
  let completion = null;
  let dropped = null;
  const ratingBlock = h("div", { hidden: true });
  const actual = slider("actual", entry.predicted_suds ?? entry.challenge.suds_target, copy.evening.actual, copy.suds.scale);
  const predictedLate = entry.predicted_suds === null
    ? slider("predicted_late", entry.challenge.suds_target, copy.evening.predictedLate) : null;
  const droppedSeg = seg("dropped", [[true, copy.evening.yes], [false, copy.evening.no]], null, (v) => (dropped = v));
  ratingBlock.append(
    predictedLate || "", actual,
    h("label", {}, copy.evening.dropped(entry.challenge.safety_trap_to_drop)), droppedSeg,
  );
  const note = h("input", { type: "text", maxlength: 500, placeholder: copy.evening.notePlaceholder });
  const save = h("button", { class: "btn block", type: "submit", disabled: true }, copy.evening.save);
  const completionSeg = seg("completion",
    [["full", copy.completion.full], ["partial", copy.completion.partial], ["none", copy.completion.none]],
    null,
    (v) => { completion = v; ratingBlock.hidden = v === "none"; save.disabled = false; });

  const form = h("form", {
    style: "margin-top:12px",
    onsubmit: (e) => {
      e.preventDefault();
      act(async () => {
        const approached = completion !== "none";
        state.result = await api.logOutcome(entry.id, {
          completion,
          actual_suds: approached ? Number(form.elements.actual.value) : null,
          predicted_suds: approached && predictedLate ? Number(form.elements.predicted_late.value) : null,
          safety_dropped: approached ? dropped : null,
          what_happened: note.value || null,
        });
        state.eveningFor = null;
      });
    },
  },
    h("h3", {}, copy.evening.title),
    h("label", {}, copy.evening.howFar), completionSeg,
    ratingBlock,
    h("label", {}, copy.evening.note), note,
    save,
  );
  return form;
}

function gapMessage(entry) {
  if (entry.completion === "none") return copy.result.none;
  const p = entry.predicted_suds, a = entry.actual_suds, g = entry.prediction_gap;
  if (g === null) return copy.result.noPrediction;
  if (g > 0) return copy.result.easier(p, a, g);
  if (g === 0) return copy.result.same(p);
  return copy.result.harder(p, a);
}

function resultCard(result) {
  const titleName = (k) => copy.titles[k]?.name ?? k;
  const events = result.events.map((ev) =>
    h("p", { class: "event" },
      ev.type === "title" ? copy.events.title(titleName(ev.key))
        : ev.type === "tier_unlocked" ? copy.events.tier_unlocked(ev.tier)
        : copy.events.comeback),
  );
  return h("div", { class: `card ${result.entry.completion === "none" ? "soft" : "good"}` },
    h("p", { style: "margin-top:0" }, gapMessage(result.entry)),
    result.entry.completion === "partial" ? h("p", {}, copy.result.partial) : null,
    ...events,
    h("button", { class: "link", onclick: () => { state.result = null; render(); } }, "OK"),
  );
}

function loggedCard(entry) {
  return h("div", { class: "card" },
    h("div", { class: "text", style: "font-weight:600" }, entry.challenge.text),
    h("p", { class: "kv" }, h("b", {}, copy.completion[entry.completion]), entry.what_happened ? ` · ${entry.what_happened}` : ""),
    h("p", { class: "kv" }, gapMessage(entry)),
    h("p", { class: "muted" }, copy.today.done),
  );
}

// ---------------------------------------------------------------- PROGRESS

let showTable = false;

async function renderProgress() {
  const [p, hist] = await Promise.all([api.progress(8), api.history(12)]);
  const P = copy.progress;
  const thisWeek = p.weeks[p.weeks.length - 1];

  const stat = (n, l) => h("div", { class: "stat" }, h("div", { class: "n" }, n), h("div", { class: "l" }, l));
  const chartBox = h("div", { class: "chart" });
  const table = h("table", {},
    h("thead", {}, h("tr", {}, ...P.tableHead.map((x) => h("th", {}, x)))),
    h("tbody", {}, ...p.weeks.map((w) => h("tr", {},
      h("td", {}, fmtDate(w.week_start, { day: "numeric", month: "short" })),
      h("td", {}, String(w.approaches)), h("td", {}, String(w.full)), h("td", {}, String(w.freezes)),
      h("td", {}, w.mean_gap === null ? "–" : String(w.mean_gap)),
    ))),
  );

  const tiers = Object.entries(p.gap_by_tier);
  viewEl.replaceChildren(
    h("h2", {}, P.heading),
    h("div", { class: "stats" },
      stat(`${thisWeek.score}/${p.week_target}`, P.thisWeek),
      stat(p.totals.pct_full === null ? "–" : `${p.totals.pct_full}%`, P.fullPct),
      stat(String(p.totals.approaches), P.approaches),
      stat(String(p.totals.safety_dropped), P.dropped),
    ),
    h("div", { class: "card" },
      showTable ? table : chartBox,
      h("p", { class: "muted small" }, P.chartGapNote),
      h("button", { class: "link", onclick: () => { showTable = !showTable; render(); } }, showTable ? P.hideTable : P.showTable),
    ),
    h("h3", {}, P.byTier),
    tiers.length
      ? h("div", { class: "card" }, h("table", {},
          h("thead", {}, h("tr", {}, ...P.byTierHead.map((x) => h("th", {}, x)))),
          h("tbody", {}, ...tiers.map(([t, g]) => h("tr", {},
            h("td", {}, copy.tierLabel(Number(t))), h("td", {}, String(g.count)),
            h("td", {}, g.early === null ? "–" : String(g.early)),
            h("td", {}, g.recent === null ? String(g.mean) : String(g.recent)),
          )))))
      : h("p", { class: "muted" }, P.byTierEmpty),
    h("h3", {}, P.history),
    hist.length
      ? h("div", { class: "card" }, ...hist.map((e) => h("div", { class: "history-item" },
          h("div", { class: "row small muted" },
            h("span", {}, fmtDate(e.date, { weekday: "short", day: "numeric", month: "short" })),
            h("span", {}, e.completion ? copy.completion[e.completion] : P.notLogged),
          ),
          h("div", {}, e.challenge.text),
          e.prediction_gap !== null
            ? h("div", { class: "small muted" }, `${e.predicted_suds} → ${e.actual_suds}`, e.what_happened ? ` · ${e.what_happened}` : "")
            : e.what_happened ? h("div", { class: "small muted" }, e.what_happened) : null,
        )))
      : h("p", { class: "muted" }, P.historyEmpty),
  );
  if (!showTable) renderWeeklyChart(chartBox, p.weeks, p.week_target, P);
}

// ---------------------------------------------------------------- YOU

async function renderYou() {
  const [titles, t] = await Promise.all([api.titles(), api.today()]);
  const Y = copy.you;
  const tierSeg = seg("tier",
    Array.from({ length: t.tier.unlocked }, (_, i) => [i + 1, copy.tierLabel(i + 1)]),
    t.tier.current,
    (v) => act(() => api.setTier(v)));
  tierSeg.classList.add("grid2");

  viewEl.replaceChildren(
    h("h2", {}, Y.titles),
    h("div", { class: "titles" }, ...titles.map((x) => {
      const c = copy.titles[x.key] ?? { name: x.key, hint: "" };
      return h("div", { class: `title-card ${x.earned_at ? "" : "locked"}` },
        h("div", { class: "name" }, c.name),
        h("div", { class: "small muted" }, x.earned_at ? Y.earned(fmtDate(x.earned_at.slice(0, 10), { day: "numeric", month: "short" })) : c.hint),
      );
    })),
    h("h2", {}, Y.tierHeading),
    h("p", { class: "muted small" }, Y.tierHelp),
    tierSeg,
    errorBox(),
    h("h2", {}, Y.about),
    h("p", { class: "muted small" }, copy.disclaimer),
  );
}

// ---------------------------------------------------------------- boot

document.getElementById("brand").textContent = copy.appName;
document.title = copy.appName;
renderNav();
render();
