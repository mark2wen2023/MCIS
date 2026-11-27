// src/analysis/derive.ts
function isRegisteredView(c) {
  return Array.isArray(c.registeredIdentities) && c.registeredIdentities.length > 0;
}
function vesselName(c, id) {
  return c.vessels.find((v) => v.vesselId === id)?.name ?? id;
}
var MOMENT_COLOR = {
  collision: "#ff3b5c",
  reportCollision: "#ff8fa3",
  minClearance: "#ffb020",
  minDistance: "#a78bfa",
  minDistanceSampled: "#a78bfa",
  minDcpa: "#3be3ff",
  firstDanger: "#f97316"
};
function segmentOverlapsOpenInterval(t0, t1, start, end) {
  if (!(end > start)) return false;
  const lo = Math.min(t0, t1);
  const hi = Math.max(t0, t1);
  return lo < end && hi > start;
}
function isInsideOpenInterval(t, start, end) {
  return t > start && t < end;
}
function gapsForVessel(gaps, vesselId) {
  return (gaps ?? []).filter((g) => g.vesselId === vesselId);
}
function pairOpenGaps(gaps) {
  return gaps ?? [];
}
function insertOpenGapBreaks(points, gaps) {
  const out = [];
  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    const inside = gaps.some((g) => isInsideOpenInterval(p.t, g.startSec, g.endSec));
    const numeric = !inside && p.value != null && !Number.isNaN(Number(p.value)) ? Number(p.value) : null;
    if (i > 0 && gaps.some((g) => segmentOverlapsOpenInterval(points[i - 1].t, p.t, g.startSec, g.endSec))) {
      out.push(null);
    }
    out.push(numeric == null ? [p.t, null] : [p.t, numeric]);
  }
  return out;
}
function hasDeclaredGaps(c) {
  return Array.isArray(c.declaredOpenGaps) && c.declaredOpenGaps.length > 0;
}
function clockLookup(series2) {
  const map = new Map(series2.map((p) => [p.t, p.clock]));
  return (t) => map.get(t) ?? `t=${t}`;
}
function tooltipValue(param) {
  const raw = param.value ?? param.data;
  if (typeof raw === "number") return Number.isFinite(raw) ? raw : null;
  if (Array.isArray(raw) && raw.length >= 2) {
    const v = raw[1];
    return typeof v === "number" && Number.isFinite(v) ? v : null;
  }
  return null;
}
function tooltipTime(params) {
  const first = params[0];
  if (!first) return null;
  if (typeof first.axisValue === "number") return first.axisValue;
  const raw = first.value ?? first.data;
  if (Array.isArray(raw) && typeof raw[0] === "number") return raw[0];
  return null;
}
function gapTooltipFormatter(gaps, clockOf) {
  return (raw) => {
    const params = Array.isArray(raw) ? raw : [raw];
    const t = tooltipTime(params);
    const inside = t != null && gaps.some((g) => isInsideOpenInterval(t, g.startSec, g.endSec));
    const head = t == null ? "" : `${clockOf(t)}`;
    if (inside) return `${head}<br/>\u7F3A\u53E3\u5185\u65E0\u6307\u6807`;
    const lines = [head];
    for (const p of params) {
      const v = tooltipValue(p);
      lines.push(`${p.seriesName ?? ""}: ${v == null ? "\u2014" : v.toFixed(3)}`);
    }
    return lines.join("<br/>");
  };
}
function curveLineFlags(c) {
  if (isRegisteredView(c)) {
    return { showSymbol: true, connectNulls: false, symbol: "circle", symbolSize: 10, showAllSymbol: true };
  }
  return { showSymbol: false, connectNulls: false };
}
function curveOption(c, series2, moments) {
  const danger = c.thresholds.dangerDcpaNm;
  const shownMoments = moments.filter((m) => m.kind !== "minDistanceSampled");
  const gaps = pairOpenGaps(c.declaredOpenGaps);
  const flags = curveLineFlags(c);
  if (!hasDeclaredGaps(c)) {
    const x = series2.map((p) => p.clock);
    const near = (t) => {
      let best = 0;
      series2.forEach((p, i) => {
        if (Math.abs(p.t - t) < Math.abs(series2[best].t - t)) best = i;
      });
      return x[best];
    };
    return {
      backgroundColor: "transparent",
      animation: false,
      grid: { left: 52, right: 56, top: 40, bottom: 34 },
      legend: { top: 4, textStyle: { color: "#8da4c4", fontSize: 11 } },
      tooltip: { trigger: "axis", valueFormatter: (v) => typeof v === "number" ? v.toFixed(3) : String(v ?? "\u2014") },
      xAxis: { type: "category", data: x, axisLabel: { color: "#8da4c4", fontSize: 10 }, axisLine: { lineStyle: { color: "#33506e" } } },
      yAxis: [
        { type: "value", name: "nm", nameTextStyle: { color: "#8da4c4" }, axisLabel: { color: "#8da4c4" }, splitLine: { lineStyle: { color: "rgba(141,164,196,0.12)" } } },
        { type: "value", name: "TCPA min", nameTextStyle: { color: "#8da4c4" }, axisLabel: { color: "#8da4c4" }, splitLine: { show: false } }
      ],
      series: [
        {
          name: "\u4E24\u8239\u8DDD\u79BB D(t)",
          type: "line",
          ...flags,
          data: series2.map((p) => p.distanceNm),
          lineStyle: { color: "#3be3ff", width: 2 },
          itemStyle: { color: "#3be3ff" },
          markLine: {
            symbol: "none",
            silent: true,
            label: { color: "#e6f1ff", fontSize: 10, position: "insideEndTop", formatter: (p) => String(p.name ?? "") },
            data: shownMoments.map((m) => ({ name: m.label.replace(/（.*?）/g, ""), xAxis: near(m.t), lineStyle: { color: MOMENT_COLOR[m.kind] ?? "#8da4c4", type: "dashed" } }))
          }
        },
        {
          name: "DCPA(t)",
          type: "line",
          ...flags,
          data: series2.map((p) => p.dcpaNm),
          lineStyle: { color: "#ffb020", width: 2 },
          itemStyle: { color: "#ffb020" },
          markLine: danger !== void 0 ? {
            symbol: "none",
            silent: true,
            label: { color: "#ff8fa3", fontSize: 10, formatter: `\u5371\u9669 DCPA ${danger} nm` },
            data: [{ yAxis: danger, lineStyle: { color: "#ff3b5c", type: "dotted" } }]
          } : void 0
        },
        { name: "TCPA(t)", type: "line", yAxisIndex: 1, ...flags, data: series2.map((p) => p.tcpaMin), lineStyle: { color: "#a78bfa", width: 1.5, type: "dashed" }, itemStyle: { color: "#a78bfa" } }
      ]
    };
  }
  const clockOf = clockLookup(series2);
  const distance = insertOpenGapBreaks(series2.map((p) => ({ t: p.t, value: p.distanceNm })), gaps);
  const dcpa = insertOpenGapBreaks(series2.map((p) => ({ t: p.t, value: p.dcpaNm })), gaps);
  const tcpa = insertOpenGapBreaks(series2.map((p) => ({ t: p.t, value: p.tcpaMin })), gaps);
  return {
    backgroundColor: "transparent",
    animation: false,
    grid: { left: 52, right: 56, top: 40, bottom: 34 },
    legend: { top: 4, textStyle: { color: "#8da4c4", fontSize: 11 } },
    tooltip: { trigger: "axis", className: "w12-gap-tooltip", formatter: gapTooltipFormatter(gaps, clockOf) },
    xAxis: { type: "value", name: "s", axisLabel: { color: "#8da4c4", fontSize: 10, formatter: (t) => clockOf(Number(t)) }, axisLine: { lineStyle: { color: "#33506e" } }, splitLine: { lineStyle: { color: "rgba(141,164,196,0.12)" } } },
    yAxis: [
      { type: "value", name: "nm", nameTextStyle: { color: "#8da4c4" }, axisLabel: { color: "#8da4c4" }, splitLine: { lineStyle: { color: "rgba(141,164,196,0.12)" } } },
      { type: "value", name: "TCPA min", nameTextStyle: { color: "#8da4c4" }, axisLabel: { color: "#8da4c4" }, splitLine: { show: false } }
    ],
    series: [
      {
        name: "\u4E24\u8239\u8DDD\u79BB D(t)",
        type: "line",
        ...flags,
        data: distance,
        lineStyle: { color: "#3be3ff", width: 2 },
        itemStyle: { color: "#3be3ff" },
        markLine: {
          symbol: "none",
          silent: true,
          label: { color: "#e6f1ff", fontSize: 10, position: "insideEndTop", formatter: (p) => String(p.name ?? "") },
          data: shownMoments.map((m) => ({ name: m.label.replace(/（.*?）/g, ""), xAxis: m.t, lineStyle: { color: MOMENT_COLOR[m.kind] ?? "#8da4c4", type: "dashed" } }))
        }
      },
      {
        name: "DCPA(t)",
        type: "line",
        ...flags,
        data: dcpa,
        lineStyle: { color: "#ffb020", width: 2 },
        itemStyle: { color: "#ffb020" },
        markLine: danger !== void 0 ? {
          symbol: "none",
          silent: true,
          label: { color: "#ff8fa3", fontSize: 10, formatter: `\u5371\u9669 DCPA ${danger} nm` },
          data: [{ yAxis: danger, lineStyle: { color: "#ff3b5c", type: "dotted" } }]
        } : void 0
      },
      { name: "TCPA(t)", type: "line", yAxisIndex: 1, ...flags, data: tcpa, lineStyle: { color: "#a78bfa", width: 1.5, type: "dashed" }, itemStyle: { color: "#a78bfa" } }
    ]
  };
}
function speedTooltipFormatter(c, rows, clockOf) {
  return (raw) => {
    const params = Array.isArray(raw) ? raw : [raw];
    const t = tooltipTime(params);
    const head = t == null ? "" : `${clockOf(t)}`;
    const lines = [head];
    for (const p of params) {
      const row = rows[p.seriesIndex ?? 0];
      const inGap = t != null && row != null && gapsForVessel(c.declaredOpenGaps, row.vesselId).some((g) => isInsideOpenInterval(t, g.startSec, g.endSec));
      const v = tooltipValue(p);
      if (inGap || v == null) lines.push(`${p.seriesName ?? ""}: \u2014`);
      else lines.push(`${p.seriesName ?? ""}: ${v.toFixed(3)} kn`);
    }
    return lines.join("<br/>");
  };
}
function speedOption(c, rows) {
  const seriesRows = rows ?? c.speedSeries ?? [];
  const colors = ["#3be3ff", "#f97316"];
  const clockOf = clockLookup(seriesRows.flatMap((r) => r.points));
  return {
    backgroundColor: "transparent",
    animation: false,
    grid: { left: 52, right: 24, top: 30, bottom: 34 },
    legend: { top: 4, textStyle: { color: "#8da4c4", fontSize: 11 } },
    tooltip: { trigger: "axis", formatter: speedTooltipFormatter(c, seriesRows, clockOf) },
    xAxis: { type: "value", name: "s", axisLabel: { color: "#8da4c4", fontSize: 10, formatter: (t) => clockOf(Number(t)) }, axisLine: { lineStyle: { color: "#33506e" } }, splitLine: { lineStyle: { color: "rgba(141,164,196,0.12)" } } },
    yAxis: { type: "value", name: "kn", nameTextStyle: { color: "#8da4c4" }, axisLabel: { color: "#8da4c4" }, splitLine: { lineStyle: { color: "rgba(141,164,196,0.12)" } } },
    series: seriesRows.map((row, i) => ({
      name: row.name ?? vesselName(c, row.vesselId),
      type: "line",
      showSymbol: false,
      connectNulls: false,
      data: insertOpenGapBreaks(
        row.points.map((p) => ({ t: p.t, value: p.speedKn })),
        gapsForVessel(c.declaredOpenGaps, row.vesselId)
      ),
      lineStyle: { color: colors[i % 2], width: 2 },
      itemStyle: { color: colors[i % 2] }
    }))
  };
}

// tests/analysis-chart-gap.test.ts
var n = 0;
function assert(cond, msg) {
  n++;
  if (!cond) throw new Error(msg);
}
var gap67 = { vesselId: "A", startSec: 6, endSec: 7 };
var gap12 = { vesselId: "A", startSec: 1, endSec: 2 };
var gapExp = { vesselId: "A", startSec: 121, endSec: 127.5 };
assert(!isInsideOpenInterval(7.5, 6, 7), "5\u201310 \u7684\u4E2D\u70B9 7.5 \u4E0D\u5728 (6,7) \u5185");
assert(segmentOverlapsOpenInterval(5, 10, 6, 7), "\u5B8C\u6574\u7EBF\u6BB5 [5,10] \u4E0E (6,7) \u91CD\u53E0\uFF0C\u5FC5\u987B\u65AD\u6BB5");
assert(!isInsideOpenInterval(5, 1, 2), "0\u201310 \u7684\u4E2D\u70B9 5 \u4E0D\u5728 (1,2) \u5185");
assert(segmentOverlapsOpenInterval(0, 10, 1, 2), "\u5B8C\u6574\u7EBF\u6BB5 [0,10] \u4E0E (1,2) \u91CD\u53E0\uFF0C\u5FC5\u987B\u65AD\u6BB5");
assert(!segmentOverlapsOpenInterval(5, 6, 6, 7), "[5,6] \u53EA\u5728\u7AEF\u70B9\u76F8\u89E6\uFF0C\u4E0D\u65AD");
assert(segmentOverlapsOpenInterval(6, 7, 6, 7), "[6,7] \u8986\u76D6\u5F00\u533A\u95F4\u5185\u90E8\uFF0C\u8981\u65AD");
assert(!segmentOverlapsOpenInterval(7, 10, 6, 7), "[7,10] \u53EA\u5728\u7AEF\u70B9\u76F8\u89E6\uFF0C\u4E0D\u65AD");
assert(segmentOverlapsOpenInterval(120, 125, 121, 127.5), "[120,125] \u4E0E expanded \u7F3A\u53E3\u91CD\u53E0");
assert(segmentOverlapsOpenInterval(120, 130, 121, 127.5), "[120,130] \u4E0E expanded \u7F3A\u53E3\u91CD\u53E0");
var grid = insertOpenGapBreaks(
  [{ t: 0, value: 1 }, { t: 5, value: 1.1 }, { t: 10, value: 1.2 }, { t: 14, value: 1.3 }],
  [gap67]
);
assert(grid.some((p) => p === null), "\u5C55\u793A\u683C 5\u219210 \u5FC5\u987B\u5728 option \u4E2D\u51FA\u73B0\u88F8 null \u65AD\u70B9");
var idx5 = grid.findIndex((p) => Array.isArray(p) && p[0] === 5);
var idx10 = grid.findIndex((p) => Array.isArray(p) && p[0] === 10);
assert(idx5 >= 0 && idx10 > idx5 && grid.slice(idx5, idx10 + 1).includes(null), "null \u5FC5\u987B\u843D\u5728 5 \u4E0E 10 \u4E4B\u95F4");
var ends = insertOpenGapBreaks(
  [{ t: 5, value: 1 }, { t: 6, value: 1.05 }, { t: 7, value: 1.06 }, { t: 10, value: 1.2 }],
  [gap67]
);
var at6 = ends.find((p) => Array.isArray(p) && p[0] === 6);
var at7 = ends.find((p) => Array.isArray(p) && p[0] === 7);
assert(at6[1] === 1.05 && at7[1] === 1.06, "6\u30017 \u7AEF\u70B9\u5FC5\u987B\u4FDD\u7559\u6570\u503C");
var i6 = ends.findIndex((p) => Array.isArray(p) && p[0] === 6);
var i7 = ends.findIndex((p) => Array.isArray(p) && p[0] === 7);
assert(ends.slice(i6, i7 + 1).includes(null), "6 \u4E0E 7 \u4E4B\u95F4\u5FC5\u987B\u65AD");
var interior = insertOpenGapBreaks(
  [{ t: 6, value: 1 }, { t: 6.5, value: 0 }, { t: 7, value: 1 }],
  [gap67]
);
var mid = interior.find((p) => Array.isArray(p) && p[0] === 6.5);
assert(mid[1] === null, "\u7F3A\u53E3\u5185\u90E8\u5373\u4F7F\u4F20\u5165 0 \u4E5F\u4E0D\u80FD\u4F5C\u4E3A\u6307\u6807\u8F93\u51FA");
var inferred = insertOpenGapBreaks(
  [{ t: 0, value: 1 }, { t: 5, value: 1.1 }, { t: 10, value: 1.2 }],
  []
);
assert(!inferred.some((p) => p === null), "\u6CA1\u6709\u663E\u5F0F\u7F3A\u53E3\u65F6\u4E0D\u5F97\u56E0\u6B65\u957F\u63A8\u65AD\u65AD\u6BB5");
function fakeCase(gaps, series2) {
  return {
    caseId: "SYN-UNIT",
    key: "unit",
    title: "unit",
    isFictionalDemo: true,
    sourceLabel: "synthetic",
    sourceRefs: [],
    epochLocal: "2026-02-01 20:00:00",
    timeZone: "Asia/Shanghai",
    vessels: [{ vesselId: "A", name: "A" }, { vesselId: "B", name: "B" }],
    thresholds: { dangerDcpaNm: 0.25 },
    baseline: { label: "unit", stepSec: 5, cutAtSec: 14, series: series2, keyMoments: [] },
    whatif: null,
    notes: [],
    meta: {
      seedSha256: "a".repeat(64),
      seedVerified: true,
      generatedAt: "",
      generator: "unit",
      coreVersion: "unit",
      coreDll: { path: "x", sha256: "b".repeat(64), role: "x" },
      w14Export: { path: "x", sha256: "b".repeat(64), role: "x" },
      w14Frozen: { path: "x", sha256: "b".repeat(64), role: "x" },
      crossCheck: { against: [], valuesCompared: 0, maxAbsDiff: 0, tolerance: 0, ok: true },
      disclaimer: ""
    },
    declaredOpenGaps: gaps
  };
}
var series = [
  { t: 0, clock: "20:00:00", distanceNm: 1, dcpaNm: 0.4, tcpaMin: 3, riskLevel: "Safe" },
  { t: 5, clock: "20:00:05", distanceNm: 1.1, dcpaNm: 0.41, tcpaMin: 3, riskLevel: "Safe" },
  { t: 10, clock: "20:00:10", distanceNm: 1.2, dcpaNm: 0.42, tcpaMin: 3, riskLevel: "Safe" },
  { t: 14, clock: "20:00:14", distanceNm: 1.3, dcpaNm: 0.43, tcpaMin: 3, riskLevel: "Safe" }
];
var plain = curveOption(fakeCase(void 0, series), series, []);
assert(plain.xAxis.type === "category" && plain.series.length === 3, "\u65E0\u7F3A\u53E3\u65F6\u4FDD\u6301\u539F category \u66F2\u7EBF");
assert(plain.series.map((s) => s.name).join("|") === "\u4E24\u8239\u8DDD\u79BB D(t)|DCPA(t)|TCPA(t)", "\u4E09\u6761\u66F2\u7EBF\u540D\u4E0D\u53D8");
assert(!plain.series.some((s) => s.data.includes(null)), "\u65E0\u7F3A\u53E3\u5B57\u6BB5\u65F6\u6570\u636E\u4E2D\u65E0 null \u65AD\u70B9");
var broken = curveOption(fakeCase([gap67], series), series, []);
assert(broken.xAxis.type === "value", "\u6709\u663E\u5F0F\u7F3A\u53E3\u65F6\u7528\u6570\u503C\u8F74\u4EE5\u4FBF\u63D2\u5165\u65AD\u70B9");
assert(typeof broken.tooltip.formatter === "function", "\u7F3A\u53E3 tooltip \u4F7F\u7528\u81EA\u5B9A\u4E49 formatter");
for (const s of broken.series) {
  assert(s.connectNulls === false, `${s.name} connectNulls=false`);
  assert(s.data.includes(null), `${s.name} \u7684 ECharts data \u542B\u88F8 null \u65AD\u70B9`);
}
var withSpeed = fakeCase([gap67], series);
withSpeed.speedSeries = [
  { vesselId: "A", name: "A", points: [{ t: 5, clock: "20:00:05", speedKn: 5.5 }, { t: 6, clock: "20:00:06", speedKn: 5.5 }, { t: 7, clock: "20:00:07", speedKn: 5.5 }, { t: 10, clock: "20:00:10", speedKn: 5.5 }] },
  { vesselId: "B", name: "B", points: [{ t: 5, clock: "20:00:05", speedKn: 6 }, { t: 6, clock: "20:00:06", speedKn: 6 }, { t: 6.5, clock: "20:00:06.500", speedKn: 6 }, { t: 7, clock: "20:00:07", speedKn: 6 }, { t: 10, clock: "20:00:10", speedKn: 6 }] }
];
var sp = speedOption(withSpeed);
var aLine = sp.series.find((s) => s.name === "A");
var bLine = sp.series.find((s) => s.name === "B");
assert(aLine.data.includes(null), "\u7F3A\u8F68\u8239\u8239\u901F\u5FC5\u987B\u65AD\u6BB5");
assert(!bLine.data.includes(null), "\u5BF9\u7167\u8239\u8239\u901F\u4E0D\u5F97\u88AB\u6539\u5199\u65AD\u6BB5");
var b65 = bLine.data.find((p) => Array.isArray(p) && p[0] === 6.5);
assert(b65[1] === 6, "\u5BF9\u7167\u8239\u5728 6.5 \u7684\u539F\u59CB\u8239\u901F\u4FDD\u7559");
var offset = insertOpenGapBreaks(
  [{ t: 0, value: 2 }, { t: 10, value: 2.2 }],
  [gap12]
);
assert(offset.includes(null), "\u975E\u5C45\u4E2D (1,2) \u5728 0/10 \u6BB5\u4E5F\u5FC5\u987B\u5199\u5165 null");
var exp = insertOpenGapBreaks(
  [{ t: 120, value: 1.07 }, { t: 125, value: 0 }, { t: 130, value: 1.01 }],
  [gapExp]
);
var p125 = exp.find((p) => Array.isArray(p) && p[0] === 125);
assert(p125[1] === null && exp.includes(null), "expanded \u683C\u70B9 125 \u4E0D\u5F97\u8F93\u51FA\u9020\u96F6\uFF0C\u4E14 120\u2013130 \u65AD\u6BB5");
console.log(`W12 chart-gap unit tests: ${n} passed`);
