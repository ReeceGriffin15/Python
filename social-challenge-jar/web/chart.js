// Weekly chart: approaches (bars) above, prediction gap (line) below, sharing
// one week axis. Two panels instead of a dual axis - different units, different scales.

const NS = "http://www.w3.org/2000/svg";

function s(tag, attrs = {}, text) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (text !== undefined) el.textContent = text;
  return el;
}

const fmtWeek = (iso) =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" });

// bar with 4px rounded top, flat on the baseline
function barPath(x, y, w, h, r = 4) {
  r = Math.min(r, h, w / 2);
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}

export function renderWeeklyChart(container, weeks, target, copy) {
  const W = 360, H = 280, L = 30, R = 6;  // ~1:1 with a phone-width card, so 11px text stays 11px
  const P1 = { top: 30, h: 90 }, P2 = { top: 170, h: 80 };
  const n = weeks.length;
  const band = (W - L - R) / n;
  const cx = (i) => L + band * i + band / 2;

  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${copy.chartApproaches}; ${copy.chartGap}` });

  // ---- panel 1: approaches
  const maxA = Math.max(target, ...weeks.map((w) => w.approaches), 1);
  const y1 = (v) => P1.top + P1.h - (v / maxA) * P1.h;
  svg.append(s("text", { x: 0, y: 14, class: "panel-title" }, copy.chartApproaches));
  svg.append(s("line", { x1: L, x2: W - R, y1: y1(0), y2: y1(0), class: "grid" }));
  svg.append(s("line", { x1: L, x2: W - R, y1: y1(target), y2: y1(target), class: "target" }));
  svg.append(s("text", { x: L - 6, y: y1(target) + 4, "text-anchor": "end", class: "tick" }, String(target)));
  svg.append(s("text", { x: L - 6, y: y1(0) + 4, "text-anchor": "end", class: "tick" }, "0"));
  svg.append(s("text", { x: W - R, y: y1(target) - 5, "text-anchor": "end", class: "tick" }, copy.target(target)));
  const bw = Math.min(24, band * 0.6);
  weeks.forEach((w, i) => {
    if (!w.approaches) return;
    const y = y1(w.approaches);
    svg.append(s("path", { d: barPath(cx(i) - bw / 2, y, bw, y1(0) - y), class: "bar" }));
  });
  // direct label on the current week only
  const last = weeks[n - 1];
  if (last.approaches) {
    svg.append(s("text", { x: cx(n - 1), y: y1(last.approaches) - 5, "text-anchor": "middle", class: "tick" }, String(last.approaches)));
  }

  // ---- panel 2: prediction gap
  const gaps = weeks.map((w) => w.mean_gap).filter((g) => g !== null);
  const gMax = Math.max(10, ...gaps.map((g) => Math.ceil(g / 10) * 10));
  const gMin = Math.min(0, ...gaps.map((g) => Math.floor(g / 10) * 10));
  const y2 = (v) => P2.top + P2.h - ((v - gMin) / (gMax - gMin)) * P2.h;
  svg.append(s("text", { x: 0, y: P2.top - 16, class: "panel-title" }, copy.chartGap));
  for (const v of new Set([gMin, 0, gMax])) {
    svg.append(s("line", { x1: L, x2: W - R, y1: y2(v), y2: y2(v), class: v === 0 ? "zero" : "grid" }));
    svg.append(s("text", { x: L - 6, y: y2(v) + 4, "text-anchor": "end", class: "tick" }, v > 0 ? `+${v}` : String(v)));
  }
  // line, broken across weeks with no data
  let seg = [];
  const flush = () => {
    if (seg.length > 1) svg.append(s("polyline", { points: seg.join(" "), class: "gap-line" }));
    seg = [];
  };
  weeks.forEach((w, i) => (w.mean_gap === null ? flush() : seg.push(`${cx(i)},${y2(w.mean_gap)}`)));
  flush();
  weeks.forEach((w, i) => {
    if (w.mean_gap !== null) svg.append(s("circle", { cx: cx(i), cy: y2(w.mean_gap), r: 4, class: "gap-dot" }));
  });

  // ---- shared x axis
  weeks.forEach((w, i) => {
    if (n > 5 && (n - 1 - i) % 2) return;  // label alternate weeks, always the current one
    svg.append(s("text", { x: cx(i), y: H - 4, "text-anchor": "middle", class: "tick" }, fmtWeek(w.week_start)));
  });

  // ---- hover: one hit column per week spanning both panels
  const hoverCol = s("rect", { y: P1.top - 6, width: band, height: P2.top + P2.h - P1.top + 12, class: "hover-col", visibility: "hidden" });
  svg.append(hoverCol);
  const tip = document.createElement("div");
  tip.className = "tooltip";
  tip.hidden = true;
  weeks.forEach((w, i) => {
    const hit = s("rect", { x: L + band * i, y: 0, width: band, height: H, class: "hit" });
    const show = () => {
      hoverCol.setAttribute("x", L + band * i);
      hoverCol.setAttribute("visibility", "visible");
      tip.replaceChildren(
        Object.assign(document.createElement("div"), { textContent: copy.tooltipWeek(fmtWeek(w.week_start)) }),
        Object.assign(document.createElement("div"), { textContent: copy.tooltipApproaches(w.approaches) }),
        Object.assign(document.createElement("div"), { textContent: copy.tooltipGap(w.mean_gap) }),
      );
      tip.style.left = `${(cx(i) / W) * 100}%`;
      tip.style.top = `${(P1.top / H) * 100}%`;
      tip.hidden = false;
    };
    hit.addEventListener("pointerenter", show);
    hit.addEventListener("pointerdown", show);
    svg.append(hit);
  });
  svg.addEventListener("pointerleave", () => {
    hoverCol.setAttribute("visibility", "hidden");
    tip.hidden = true;
  });

  container.replaceChildren(svg, tip);
}
