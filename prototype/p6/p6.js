  <script>
  // ============================================================================
  // P6+ 国际对标模块：SVG 渲染（所有图形仅用 线段/折线/矩形/圆/多边形/文字，可一一映射到 UI Toolkit Painter2D + Label）
  // 全部为虚构演示数据（Lily × Mary），不含任何真实事故内容
  // ============================================================================
  (function () {
    var C = { cyan: "#3be3ff", amber: "#ffb020", red: "#ff3b5c", green: "#10b981", purple: "#a78bfa", text: "#e6f1ff", sec: "#8da4c4", muted: "#526987", grid: "rgba(141,164,196,0.14)", line: "rgba(59,227,255,0.22)" };
    function svg(w, h, body) { return '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg">' + body + '</svg>'; }
    function t(x, y, s, o) { o = o || {}; return '<text x="' + x + '" y="' + y + '" fill="' + (o.fill || C.sec) + '" font-size="' + (o.size || 11) + '"' + (o.anchor ? ' text-anchor="' + o.anchor + '"' : '') + (o.weight ? ' font-weight="' + o.weight + '"' : '') + (o.mono ? ' font-family="ui-monospace,Consolas,monospace"' : '') + '>' + s + '</text>'; }
    function r(x, y, w, h, fill, stroke, rx, extra) { return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="' + (rx || 0) + '" fill="' + (fill || "none") + '"' + (stroke ? ' stroke="' + stroke + '"' : '') + (extra || '') + '/>'; }
    function l(x1, y1, x2, y2, stroke, w, dash) { return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" stroke="' + stroke + '" stroke-width="' + (w || 1) + '"' + (dash ? ' stroke-dasharray="' + dash + '"' : '') + '/>'; }
    function pl(pts, stroke, w, dash, fill) { return '<polyline points="' + pts.map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ') + '" fill="' + (fill || 'none') + '" stroke="' + stroke + '" stroke-width="' + (w || 1.5) + '"' + (dash ? ' stroke-dasharray="' + dash + '"' : '') + ' stroke-linejoin="round"/>'; }
    function arrow(x1, y1, x2, y2, col) {
      var a = Math.atan2(y2 - y1, x2 - x1), s = 6;
      return l(x1, y1, x2, y2, col, 1.3) + '<polygon points="' + x2 + ',' + y2 + ' ' + (x2 - s * Math.cos(a - 0.45)) + ',' + (y2 - s * Math.sin(a - 0.45)) + ' ' + (x2 - s * Math.cos(a + 0.45)) + ',' + (y2 - s * Math.sin(a + 0.45)) + '" fill="' + col + '"/>';
    }
    function put(id, html) { var el = document.getElementById(id); if (el) el.innerHTML = html; }
    function seeded(seed) { return function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }; }
    function hhmm(sec, base) { var s = base + sec; var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = Math.round(s % 60); return (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m + (ss ? ':' + (ss < 10 ? '0' : '') + ss : ''); }
    var BASE = 14 * 3600 + 15 * 60; // 14:15:00

    // ---------- 09 VDR 多轨 ----------
    function renderVdr() {
      var W = 1150, H = 262, X0 = 168, X1 = 1138, T = 750;
      var x = function (s) { return X0 + s / T * (X1 - X0); };
      var b = '';
      var lanes = [["驾驶台音频 CH1", "Mary VDR"], ["VHF CH16", "Mary VDR"], ["X 波段雷达画面", "Mary VDR · 15 s/帧"], ["ECDIS 截屏", "EV-004 · 38 张"], ["车钟", "Mary 机舱"], ["舵角", "Mary · ±35°"], ["AIS 航速 SOG", "Lily · kn"], ["AIS 航向 COG", "Mary · °"]];
      var LY = 46, LH = 26;
      for (var m = 0; m <= 12; m++) { var xs = x(m * 60); b += l(xs, 34, xs, H - 4, C.grid, 1); b += t(xs, 14, hhmm(m * 60, BASE), { anchor: "middle", size: 10, mono: 1, fill: C.muted }); }
      var ev = [[210, "E2"], [338, "E3"], [435, "E4"], [500, "E5"], [540, "E6 碰撞"], [690, "E7"]];
      ev.forEach(function (e) { var xe = x(e[0]); var red = e[0] === 540; b += '<polygon points="' + (xe - 5) + ',22 ' + (xe + 5) + ',22 ' + xe + ',30" fill="' + (red ? C.red : C.amber) + '"/>' + t(xe + 7, 30, e[1], { size: 10, fill: red ? C.red : C.amber, weight: 700 }); });
      lanes.forEach(function (ln, i) {
        var y = LY + i * LH;
        b += r(4, y + 1, X0 - 12, LH - 3, i % 2 ? "rgba(13,25,43,0.6)" : "rgba(20,36,60,0.6)", null, 3);
        b += t(10, y + 12, ln[0], { size: 11, fill: C.text, weight: 600 }) + t(10, y + 22, ln[1], { size: 8.5, fill: C.muted });
        b += r(X0, y + 1, X1 - X0, LH - 3, i % 2 ? "rgba(255,255,255,0.015)" : "rgba(59,227,255,0.025)");
      });
      // 1 音频波形
      var rnd = seeded(7), y0 = LY + 12, wave = '';
      for (var s = 0; s < T; s += 2.2) {
        var talk = (s > 255 && s < 300) || (s > 400 && s < 470) || (s > 505 && s < 560) || (s > 600 && s < 660);
        var a = (talk ? 4 + rnd() * 7 : 0.6 + rnd() * 1.6) * (s > 535 && s < 548 ? 1.5 : 1);
        wave += l(x(s).toFixed(1), (y0 - a).toFixed(1), x(s).toFixed(1), (y0 + a).toFixed(1), s > 535 && s < 548 ? C.red : "rgba(59,227,255,0.75)", 1);
      }
      b += wave + t(x(540) + 4, LY + 9, "撞击声", { size: 9, fill: C.red });
      // 2 VHF
      var y2 = LY + LH;
      [[312, 340, "VTS 呼叫 Mary"], [523, 560, "Lily 呼叫 Mary"], [580, 650, "Lily 遇险呼叫"]].forEach(function (v) { b += r(x(v[0]), y2 + 5, x(v[1]) - x(v[0]), 14, "rgba(167,139,250,0.28)", C.purple, 2) + t(x(v[0]) + 3, y2 + 16, v[2], { size: 9, fill: "#ddd6fe" }); });
      // 3 雷达帧
      var y3 = LY + 2 * LH;
      for (var f = 0; f < T; f += 15) { b += r(x(f) + 1, y3 + 5, x(15) - x(0) - 2.5, 14, "rgba(16,185,129,0.12)", "rgba(16,185,129,0.45)", 1); if (f % 60 === 0) b += '<circle cx="' + (x(f) + 9) + '" cy="' + (y3 + 12) + '" r="1.6" fill="' + C.green + '"/>'; }
      // 4 ECDIS
      var y4 = LY + 3 * LH, shots = [20, 80, 140, 195, 230, 290, 330, 360, 390, 420, 432, 445, 470, 495, 520, 538, 560, 600, 660, 720];
      shots.forEach(function (s) { var xs = x(s); b += '<polygon points="' + xs + ',' + (y4 + 6) + ' ' + (xs + 5) + ',' + (y4 + 12) + ' ' + xs + ',' + (y4 + 18) + ' ' + (xs - 5) + ',' + (y4 + 12) + '" fill="rgba(255,176,32,0.35)" stroke="' + C.amber + '" stroke-width="1"/>'; });
      // 5 车钟
      var y5 = LY + 4 * LH, lv = function (k) { return y5 + 5 + k * 4.5; };
      b += pl([[x(0), lv(0)], [x(248), lv(0)], [x(248), lv(1)], [x(500), lv(1)], [x(500), lv(2)], [x(520), lv(2)], [x(520), lv(3.4)], [x(T), lv(3.4)]], C.amber, 1.6);
      b += t(x(4), lv(0) - 1, "前进三", { size: 8.5, fill: C.amber }) + t(x(252), lv(1) + 9, "半速", { size: 8.5, fill: C.amber }) + t(x(524), lv(3.4) - 2, "全速倒车", { size: 8.5, fill: C.amber });
      // 6 舵角
      var y6 = LY + 5 * LH, ym = y6 + 12, rud = [];
      for (var k = 0; k <= T; k += 5) { var d = Math.sin(k / 23) * 1.5; if (k >= 435 && k < 505) d = -20; if (k >= 505 && k < 530) d = -20 + (k - 505) / 25 * 55; if (k >= 530) d = 35 - Math.min(30, (k - 530) * 0.3); rud.push([x(k), ym - d / 35 * 10]); }
      b += l(X0, ym, X1, ym, "rgba(141,164,196,0.25)", 1, "2 3") + pl(rud, C.red, 1.6) + t(x(437), ym + 12, "左 20°", { size: 9, fill: C.red, weight: 700 });
      // 7 Lily SOG
      var y7 = LY + 6 * LH, sog = [];
      for (var k2 = 0; k2 <= T; k2 += 5) { var v = 10.6 + Math.sin(k2 / 40) * 0.15; if (k2 > 490) v = 10.6 - (k2 - 490) * 0.09; if (k2 > 540) v = Math.max(0.8, 6.1 - (k2 - 540) * 0.035); sog.push([x(k2), y7 + 21 - v / 12 * 17]); }
      b += pl(sog, C.cyan, 1.6) + t(x(8), y7 + 9, "10.6", { size: 8.5, fill: C.cyan, mono: 1 });
      // 8 Mary COG
      var y8 = LY + 7 * LH, cog = [];
      for (var k3 = 0; k3 <= T; k3 += 5) { var c = 8 + Math.sin(k3 / 30) * 0.8; if (k3 > 435) c = 8 - Math.min(26, (k3 - 435) * 0.32); if (k3 > 540) c = -18 + Math.sin(k3 / 15) * 1.5; cog.push([x(k3), y8 + 12 - (c - 8) / 30 * 10]); }
      b += pl(cog, "#ff8fa3", 1.6) + t(x(8), y8 + 9, "008°", { size: 8.5, fill: "#ff8fa3", mono: 1 }) + t(x(560), y8 + 21, "342°", { size: 8.5, fill: "#ff8fa3", mono: 1 });
      // 碰撞线 + 播放头
      b += l(x(540), 34, x(540), H - 4, C.red, 1.2, "4 3");
      var px = x(435);
      b += r(px - 1, 34, 2, H - 38, C.cyan) + r(px - 34, 33, 68, 15, "#06121f", C.cyan, 3) + t(px, 44, "14:22:15", { anchor: "middle", size: 10, fill: C.cyan, mono: 1, weight: 700 });
      put("ev-vdr-svg", svg(W, H, b));
    }

    // ---------- 09 时钟偏差 ----------
    function renderClock() {
      var W = 520, H = 140, CX = 330, SC = 2.0, b = '';
      b += t(8, 14, "时钟偏差（相对基准，秒）· 误差条 = 不确定度", { size: 10, fill: C.muted });
      for (var g = -60; g <= 80; g += 20) { var xg = CX + g * SC; b += l(xg, 20, xg, H - 14, g === 0 ? "rgba(59,227,255,0.5)" : C.grid, 1); b += t(xg, H - 3, (g > 0 ? "+" : "") + g, { anchor: "middle", size: 9, fill: C.muted, mono: 1 }); }
      var rows = [["Lily S-VDR（基准）", 0, 0.1, C.green], ["VTS 岸基 AIS", 0.4, 1, C.green], ["Mary VDR", -42.6, 0.5, C.amber], ["Mary ECDIS", 3.1, 1, C.green], ["车钟记录纸", 65, 10, C.red], ["笔录口述时间", 0, 60, C.purple]];
      rows.forEach(function (rw, i) {
        var y = 26 + i * 17.5;
        b += t(8, y + 8, rw[0], { size: 10.5, fill: C.text });
        var x2 = CX + rw[1] * SC;
        b += r(Math.min(CX, x2), y + 1, Math.max(2, Math.abs(x2 - CX)), 9, rw[3], null, 1, ' opacity="0.75"');
        var e1 = Math.max(CX - 64 * SC, x2 - rw[2] * SC), e2 = Math.min(CX + 84 * SC, x2 + rw[2] * SC);
        b += l(e1, y + 5.5, e2, y + 5.5, rw[3], 1) + l(e1, y + 2, e1, y + 9, rw[3], 1) + l(e2, y + 2, e2, y + 9, rw[3], 1);
        b += t(Math.min(e2 + 5, 470), y + 9, (rw[1] > 0 ? "+" : "") + rw[1] + (rw[2] >= 10 ? " ±" + rw[2] : ""), { size: 9.5, fill: rw[3], mono: 1 });
      });
      put("ev-clock-svg", svg(W, H, b));
    }

    // ---------- 10 陈述 vs 数据时间线 ----------
    function renderIvTimeline() {
      var W = 380, H = 100, X0 = 60, X1 = 368, T0 = 16 * 60, T1 = 25 * 60, b = '';
      var x = function (mmss) { return X0 + (mmss - T0) / (T1 - T0) * (X1 - X0); };
      for (var m = 16; m <= 25; m++) { var xm = x(m * 60); b += l(xm, 14, xm, 80, C.grid, 1); b += t(xm, 92, "14:" + m, { anchor: "middle", size: 8.5, fill: C.muted, mono: 1 }); }
      b += t(4, 30, "笔录陈述", { size: 10, fill: C.amber }) + t(4, 66, "VDR/AIS", { size: 10, fill: C.cyan });
      b += l(X0, 26, X1, 26, "rgba(255,176,32,0.3)", 1) + l(X0, 62, X1, 62, "rgba(59,227,255,0.3)", 1);
      var pairs = [[17 * 60, 17 * 60, 0], [19 * 60, 19 * 60 + 8, 0], [23 * 60, 22 * 60 + 15, 1], [20 * 60, 20 * 60 + 12, 0], [23 * 60 + 30, 23 * 60 + 34, 0]];
      pairs.forEach(function (p) { var col = p[2] ? C.red : C.green; b += l(x(p[0]), 30, x(p[1]), 58, col, 1.2, p[2] ? "" : "3 2") + '<circle cx="' + x(p[0]) + '" cy="26" r="4" fill="' + C.amber + '"/><circle cx="' + x(p[1]) + '" cy="62" r="4" fill="' + C.cyan + '"/>'; });
      b += t(x(22 * 60 + 40), 46, "Δ45 s", { size: 10, fill: C.red, weight: 700 });
      // 声号：陈述有、数据无
      var xs = x(23 * 60 + 5); b += '<rect x="' + (xs - 4) + '" y="10" width="8" height="8" fill="' + C.red + '"/>' + t(xs - 7, 18, "陈述“一长声” · 数据中无", { size: 9, fill: "#ff8fa3", anchor: "end" });
      put("iv-timeline-svg", svg(W, H, b));
    }

    // ---------- 11 会遇局面时间带 ----------
    function renderColreg() {
      var W = 1150, H = 240, X0 = 150, X1 = 1138, T = 540, b = '';
      var x = function (s) { return X0 + s / T * (X1 - X0); };
      for (var m = 0; m <= 9; m++) { var xm = x(m * 60); b += l(xm, 18, xm, H - 16, C.grid, 1); b += t(xm, 12, hhmm(m * 60, BASE), { anchor: "middle", size: 10, fill: C.muted, mono: 1 }); }
      var rows = ["会遇局面 / 适用规则", "Lily 轮责任", "Mary 轮责任", "Lily 实际操纵", "Mary 实际操纵"];
      rows.forEach(function (rw, i) { var y = 20 + i * 27; b += r(4, y, X0 - 12, 23, "rgba(20,36,60,0.6)", null, 3) + t(10, y + 15, rw, { size: 11, fill: C.text, weight: 600 }); });
      var ph = [[0, 150, "无碰撞危险", "rgba(16,185,129,0.22)", C.green], [150, 330, "能见度不良 · 未互见  R19 + R9 狭水道", "rgba(59,227,255,0.18)", C.cyan], [330, 450, "互见 · 对遇局面  R14 + R9", "rgba(255,176,32,0.22)", C.amber], [450, 540, "紧迫危险  R17(b) / R2(b)", "rgba(255,59,92,0.26)", C.red]];
      ph.forEach(function (p) { b += r(x(p[0]) + 1, 21, x(p[1]) - x(p[0]) - 2, 21, p[3], p[4], 2) + t(x(p[0]) + 6, 35, p[2], { size: 10.5, fill: "#fff", weight: 600 }); });
      var duty = [[0, 150, "保持航向航速", C.muted], [150, 330, "安全航速 · 避免向左转 · 雾号", C.cyan], [330, 450, "向右转向（双方均负让路责任，无直航船）", C.amber], [450, 540, "最有助避碰行动", C.red]];
      [0, 1].forEach(function (k) { var y = 47 + k * 27; duty.forEach(function (p) { b += r(x(p[0]) + 1, y + 1, x(p[1]) - x(p[0]) - 2, 19, "rgba(13,25,43,0.9)", p[3], 2) + t(x(p[0]) + 6, y + 14, p[2], { size: 10, fill: C.text }); }); });
      var actL = [[372, "右转 10°", C.cyan], [470, "右满舵", C.cyan], [520, "全速倒车", C.cyan]];
      var actM = [[248, "车钟半速", C.amber], [435, "左舵 20°（违反 R14）", C.red], [500, "停车", C.amber]];
      [actL, actM].forEach(function (acts, k) { var y = 101 + k * 27 + 11; b += l(X0, y, X1, y, "rgba(141,164,196,0.15)", 1); acts.forEach(function (a) { var xa = x(a[0]); b += '<circle cx="' + xa + '" cy="' + y + '" r="4.5" fill="' + a[2] + '"/>' + t(xa + 7, y + 4, a[1], { size: 10, fill: a[2], weight: 600 }); }); });
      // DCPA 曲线
      var cy0 = 160, cy1 = H - 18, maxd = 1.2;
      var yd = function (d) { return cy1 - d / maxd * (cy1 - cy0); };
      b += r(X0, cy0, X1 - X0, cy1 - cy0, "rgba(255,255,255,0.015)");
      b += r(X0, yd(0.3), X1 - X0, cy1 - yd(0.3), "rgba(255,59,92,0.10)") + l(X0, yd(1), X1, yd(1), C.amber, 1, "4 3") + l(X0, yd(0.3), X1, yd(0.3), C.red, 1, "4 3");
      b += t(X0 - 6, yd(1) + 3, "1.0 nm", { anchor: "end", size: 9, fill: C.amber, mono: 1 }) + t(X0 - 6, yd(0.3) + 3, "0.3 nm", { anchor: "end", size: 9, fill: C.red, mono: 1 }) + t(10, cy0 + 12, "DCPA (nm)", { size: 10.5, fill: C.text, weight: 600 });
      var pts = [[0, 0.95], [60, 0.82], [120, 0.66], [180, 0.52], [240, 0.42], [300, 0.33], [338, 0.29], [372, 0.27], [400, 0.31], [430, 0.30], [450, 0.18], [480, 0.08], [510, 0.03], [540, 0]];
      b += pl(pts.map(function (p) { return [x(p[0]), yd(p[1])]; }), C.cyan, 2);
      b += '<circle cx="' + x(540) + '" cy="' + yd(0) + '" r="4" fill="' + C.red + '"/>' + t(x(540) - 6, yd(0) - 6, "碰撞 14:24:00", { anchor: "end", size: 10, fill: C.red, weight: 700 });
      put("cr-band-svg", svg(W, H, b));
    }

    // ---------- 12 轨迹对比 ----------
    function renderWhatif() {
      var W = 560, HV = 540, H = 600, b = '';
      // 水域背景与航道（内容整体下移 40，画布高 540）
      b += r(0, 0, W, HV, "rgba(6,30,48,0.55)") + '<g transform="translate(0,40)">';
      b += r(0, -40, W, 40, "rgba(6,30,48,0)");
      for (var gx = 0; gx < W; gx += 40) b += l(gx, 0, gx, H, "rgba(59,227,255,0.05)", 1);
      for (var gy = -40; gy < H; gy += 40) b += l(0, gy, W, gy, "rgba(59,227,255,0.05)", 1);
      var left = [[170, -40], [170, 0], [176, 120], [184, 240], [178, 360], [168, H]], right = [[390, -40], [390, 0], [384, 120], [392, 240], [398, 360], [404, H]];
      b += '<polygon points="0,-40 ' + left.map(function (p) { return p.join(','); }).join(' ') + ' 0,' + H + '" fill="rgba(60,72,58,0.45)"/>';
      b += '<polygon points="' + W + ',-40 ' + right.map(function (p) { return p.join(','); }).join(' ') + ' ' + W + ',' + H + '" fill="rgba(60,72,58,0.45)"/>';
      b += pl(left, "rgba(255,176,32,0.7)", 1.2, "6 4") + pl(right, "rgba(255,176,32,0.7)", 1.2, "6 4");
      b += pl([[280, -40], [280, 120], [288, 240], [288, 360], [286, H]], "rgba(141,164,196,0.35)", 1, "3 5");
      [[184, 240, "3#", C.red], [392, 240, "4#", C.green], [176, 120, "5#", C.red], [398, 360, "2#", C.green]].forEach(function (bu) { b += '<circle cx="' + bu[0] + '" cy="' + bu[1] + '" r="5" fill="' + bu[3] + '" stroke="#fff" stroke-width="1"/>' + t(bu[0] + (bu[0] < 280 ? -22 : 9), bu[1] + 4, bu[2], { size: 10, fill: "#fff", mono: 1 }); });
      b += t(20, -16, "陆域 / 浅滩", { size: 10, fill: C.muted }) + t(W - 80, -16, "陆域 / 浅滩", { size: 10, fill: C.muted });
      // Lily 南下（西侧）
      var lily = [[246, 20], [244, 90], [242, 160], [240, 230], [236, 280], [226, 316], [214, 344]];
      b += pl(lily, C.cyan, 2.2);
      // Mary 原始（北上，左转）
      var mary0 = [[332, 455], [330, 400], [327, 350], [322, 322], [302, 304], [262, 298], [232, 304]];
      b += pl(mary0.slice(0, 6), C.red, 2.2, "7 4");
      // Mary 反事实（右转）
      var mary1 = [[332, 455], [331, 410], [334, 368], [346, 330], [358, 290], [364, 240], [366, 170], [366, 100]];
      b += pl(mary1, C.green, 2.4);
      // 碰撞点
      var cx = 238, cy = 298;
      b += '<circle cx="' + cx + '" cy="' + cy + '" r="13" fill="rgba(255,59,92,0.18)" stroke="' + C.red + '" stroke-width="1.5"/>' + l(cx - 6, cy - 6, cx + 6, cy + 6, C.red, 2.2) + l(cx - 6, cy + 6, cx + 6, cy - 6, C.red, 2.2);
      b += r(60, 288, 150, 34, "rgba(6,18,31,0.92)", C.red, 3) + t(68, 302, "S0 碰撞  14:24:00.35", { size: 10.5, fill: C.red, weight: 700 }) + t(68, 316, "Lily 左舷首部 · 交角 42°", { size: 9.5, fill: C.sec });
      // 最近会遇连线
      b += l(240, 262, 360, 270, C.amber, 1.4, "4 3") + r(262, 244, 78, 18, "rgba(6,18,31,0.92)", C.amber, 3) + t(301, 257, "0.21 nm", { anchor: "middle", size: 10.5, fill: C.amber, weight: 700, mono: 1 });
      // 时间刻度点
      [[244, 90, "14:20"], [240, 230, "14:23"]].forEach(function (p) { b += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="2.5" fill="' + C.cyan + '"/>' + t(p[0] - 8, p[1] + 3, p[2], { anchor: "end", size: 9, fill: C.cyan, mono: 1 }); });
      [[330, 400, "14:20"], [334, 368, "14:21 右转"]].forEach(function (p) { b += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="2.5" fill="' + C.green + '"/>' + t(p[0] + 9, p[1] + 3, p[2], { size: 9, fill: C.green, mono: 1 }); });
      b += t(326, 345, "14:22:15 左转", { anchor: "end", size: 9, fill: "#ff8fa3", mono: 1 });
      // 船舶符号
      function ship(x0, y0, ang, col, name) { var a = ang * Math.PI / 180, L = 14, Wd = 5; var p = [[0, -L], [Wd, L * 0.6], [-Wd, L * 0.6]].map(function (q) { return [x0 + q[0] * Math.cos(a) - q[1] * Math.sin(a), y0 + q[0] * Math.sin(a) + q[1] * Math.cos(a)]; }); return '<polygon points="' + p.map(function (q) { return q[0].toFixed(1) + ',' + q[1].toFixed(1); }).join(' ') + '" fill="' + col + '" stroke="#fff" stroke-width="0.8"/>' + t(x0 + 12, y0 + 4, name, { size: 10.5, fill: col, weight: 700 }); }
      b += ship(246, 24, 180, C.cyan, "Lily（出港）") + ship(366, 104, 0, C.green, "Mary S1") + ship(332, 448, 0, "#ff8fa3", "Mary（进港）");
      b += '</g>';
      H = HV;
      // 比例尺 / 指北
      b += l(430, H - 24, 530, H - 24, "#fff", 1.5) + l(430, H - 28, 430, H - 20, "#fff", 1.5) + l(530, H - 28, 530, H - 20, "#fff", 1.5) + t(480, H - 30, "0.1 nm", { anchor: "middle", size: 10, fill: "#fff", mono: 1 });
      b += '<polygon points="520,40 528,62 520,56 512,62" fill="' + C.cyan + '"/>' + t(520, 34, "N", { anchor: "middle", size: 11, fill: C.cyan, weight: 700 });
      b += r(410, H - 96, 140, 34, "rgba(6,18,31,0.85)", C.line, 3) + t(418, H - 82, "横流 1.2 kn →", { size: 10, fill: C.sec }) + t(418, H - 68, "能见度 1.5 nm", { size: 10, fill: C.sec });
      put("wi-track-svg", svg(W, H, b));

      // 敏感性
      var W2 = 300, H2 = 128, X0 = 40, X1 = 290, Y0 = 10, Y1 = 104, s = '';
      var xs = function (v) { return X0 + v / 180 * (X1 - X0); }, ys = function (d) { return Y1 - d / 0.3 * (Y1 - Y0); };
      for (var gv = 0; gv <= 180; gv += 30) { s += l(xs(gv), Y0, xs(gv), Y1, C.grid, 1) + t(xs(gv), Y1 + 12, gv, { anchor: "middle", size: 9, fill: C.muted, mono: 1 }); }
      [0, 0.1, 0.2, 0.3].forEach(function (d) { s += t(X0 - 4, ys(d) + 3, d.toFixed(1), { anchor: "end", size: 9, fill: C.muted, mono: 1 }); });
      s += r(X0, Y0, xs(52) - X0, Y1 - Y0, "rgba(255,59,92,0.12)") + l(X0, ys(0.1), X1, ys(0.1), C.amber, 1, "4 3") + t(X1 - 2, ys(0.1) - 4, "0.1 nm 安全线", { anchor: "end", size: 9, fill: C.amber });
      var cv = []; for (var v = 0; v <= 180; v += 6) { var d = v < 52 ? 0 : Math.min(0.27, 0.27 * (1 - Math.exp(-(v - 52) / 45))); cv.push([xs(v), ys(d)]); }
      s += pl(cv, C.green, 2) + l(xs(52), Y0, xs(52), Y1, C.red, 1.2) + t(xs(52) + 3, Y0 + 10, "52 s", { size: 9.5, fill: C.red, weight: 700, mono: 1 });
      s += '<circle cx="' + xs(120) + '" cy="' + ys(0.21) + '" r="4.5" fill="' + C.green + '" stroke="#fff"/>' + t(xs(120) + 6, ys(0.21) + 14, "S1", { size: 10, fill: C.green, weight: 700 });
      s += t(X0 + 2, H2 - 2, "转向提前量 (s) → 最小距离 (nm)", { size: 9, fill: C.muted });
      put("wi-sens-svg", svg(W2, H2, s));
    }

    // ---------- 13 HFACS 链 + 工休 ----------
    function renderHf() {
      var W = 640, H = 46, b = '', boxes = [["外部 2", C.purple], ["① 组织 3", C.cyan], ["② 监督 3", C.cyan], ["③ 前提 4", C.cyan], ["④ 行为 3", C.cyan], ["E4 违规左转", C.amber], ["E6 碰撞", C.red]];
      var bw = 76, gap = 14;
      boxes.forEach(function (bx, i) { var x0 = 6 + i * (bw + gap); b += r(x0, 10, bw, 26, "rgba(13,25,43,0.95)", bx[1], 4) + t(x0 + bw / 2, 27, bx[0], { anchor: "middle", size: 10.5, fill: "#fff", weight: 600 }); if (i < boxes.length - 1) b += arrow(x0 + bw + 1, 23, x0 + bw + gap - 1, 23, C.sec); });
      put("hf-flow-svg", svg(W, H, b));

      var W2 = 560, H2 = 224, X0 = 70, X1 = 486, b2 = '';
      var xh = function (h) { return X0 + h / 24 * (X1 - X0); };
      for (var h = 0; h <= 24; h += 2) { b2 += l(xh(h), 14, xh(h), H2 - 8, h % 6 ? C.grid : "rgba(141,164,196,0.28)", 1); b2 += t(xh(h), 10, (h < 10 ? "0" : "") + h, { anchor: "middle", size: 9, fill: C.muted, mono: 1 }); }
      b2 += t(X1 + 10, 10, "当日休息", { size: 9, fill: C.muted });
      var days = [["05-12", [[0, 4], [12, 16]], [[6, 9], [19, 21]], "11.0"], ["05-13", [[0, 4], [12, 16]], [[7, 10], [17, 19]], "11.0"], ["05-14", [[0, 4], [12, 16]], [[5, 9], [18, 20]], "10.0"], ["05-15", [[0, 4], [12, 16]], [[6, 9], [16, 18], [20, 22]], "9.0"], ["05-16", [[0, 4], [12, 16]], [[7, 10]], "13.0"], ["05-17", [[0, 4], [12, 16]], [[5, 10], [17, 22]], "6.0"], ["05-18", [[0, 4], [12, 14.4]], [[6, 10.5]], "—"]];
      days.forEach(function (d, i) {
        var y = 18 + i * 28, bad = d[3] !== "—" && parseFloat(d[3]) < 10;
        b2 += t(6, y + 14, d[0] + (i === 6 ? " 事发" : ""), { size: 10, fill: i === 6 ? C.red : C.text, mono: 1 });
        b2 += r(X0, y + 2, X1 - X0, 17, "rgba(141,164,196,0.10)", null, 2);
        d[1].forEach(function (w) { b2 += r(xh(w[0]), y + 2, xh(w[1]) - xh(w[0]), 17, "#0e7490", null, 1); });
        d[2].forEach(function (w) { b2 += r(xh(w[0]), y + 2, xh(w[1]) - xh(w[0]), 17, "#7c5cff", null, 1); });
        if (bad) b2 += r(X0 - 2, y, X1 - X0 + 4, 21, "none", C.red, 3, ' stroke-width="1.4"');
        b2 += t(X1 + 12, y + 14, d[3] + (d[3] !== "—" ? " h" : ""), { size: 10.5, fill: bad ? C.red : C.green, mono: 1, weight: 700 });
      });
      var yc = 18 + 6 * 28; b2 += r(xh(14.4), yc + 2, X1 - xh(14.4), 17, "rgba(255,59,92,0.15)") + l(xh(14.4), yc - 2, xh(14.4), yc + 22, C.red, 2) + t(xh(14.4) + 4, yc + 14, "14:24 碰撞", { size: 9.5, fill: C.red, weight: 700 });
      put("hf-rest-svg", svg(W2, H2, b2));
    }

    // ---------- 14 Bow-tie + AcciMap ----------
    function renderSystemic() {
      var W = 1150, H = 300, b = '', CX = 575, CY = 170;
      var col = { x: C.red, p: C.amber, o: C.green };
      b += r(CX - 120, 8, 240, 34, "rgba(255,176,32,0.12)", C.amber, 4) + t(CX, 22, "危险源 HAZARD", { anchor: "middle", size: 9, fill: C.amber, mono: 1 }) + t(CX, 36, "狭窄航道 · 雾中双向通航", { anchor: "middle", size: 12, fill: "#fff", weight: 700 });
      b += l(CX, 42, CX, CY - 50, C.amber, 1.5);
      var threats = [["能见度不良（雾）", [["雾航程序/安全航速", "x"], ["雷达/ARPA 观测", "p"]]], ["横流影响", [["航路规划余量", "p"], ["VTS 流况播报", "o"]]], ["Mary 判断失误左转", [["BRM 交叉核查", "x"], ["船长监督", "x"]]], ["瞭望不足", [["专职瞭望", "x"], ["ARPA 碰撞报警", "x"]]], ["船间通信不畅", [["VHF 协调", "p"], ["VTS 交通组织", "p"]]]];
      var cons = [["Lily 首部进水坐沉", [["水密分舱", "p"], ["应急拖带/抢滩", "o"]]], ["人员落水 / 伤亡风险", [["救生与搜救", "o"], ["弃船演习", "o"]]], ["燃油泄漏", [["油舱封堵", "p"], ["溢油应急", "o"]]], ["航道阻塞", [["航行警告", "o"], ["沉船标示", "o"]]]];
      threats.forEach(function (th, i) {
        var y = 64 + i * 52;
        b += pl([[160, y], [300, y], [CX - 60, CY]].map(function (p, k) { return k === 2 ? [CX - 56, CY + (y - CY) * 0.18] : p; }), "rgba(141,164,196,0.45)", 1.2);
        b += r(10, y - 15, 150, 30, "rgba(13,25,43,0.95)", C.sec, 4) + t(85, y + 4, th[0], { anchor: "middle", size: 11, fill: C.text, weight: 600 });
        th[1].forEach(function (br, k) { var bx = 190 + k * 128; b += r(bx, y - 12, 112, 24, "rgba(6,18,31,0.95)", col[br[1]], 2, ' stroke-width="1.6"') + r(bx, y - 12, 4, 24, col[br[1]]) + t(bx + 59, y + 4, br[0], { anchor: "middle", size: 10.5, fill: "#fff" }); });
      });
      cons.forEach(function (cn, i) {
        var y = 86 + i * 56;
        b += pl([[CX + 56, CY + (y - CY) * 0.18], [850, y], [990, y]], "rgba(141,164,196,0.45)", 1.2);
        b += r(990, y - 15, 150, 30, "rgba(40,10,18,0.9)", C.red, 4) + t(1065, y + 4, cn[0], { anchor: "middle", size: 11, fill: "#ffd0d8", weight: 600 });
        cn[1].forEach(function (br, k) { var bx = 726 + k * 128; b += r(bx, y - 12, 112, 24, "rgba(6,18,31,0.95)", col[br[1]], 2, ' stroke-width="1.6"') + r(bx + 108, y - 12, 4, 24, col[br[1]]) + t(bx + 55, y + 4, br[0], { anchor: "middle", size: 10.5, fill: "#fff" }); });
      });
      b += '<circle cx="' + CX + '" cy="' + CY + '" r="56" fill="rgba(255,59,92,0.16)" stroke="' + C.red + '" stroke-width="2"/>' + '<circle cx="' + CX + '" cy="' + CY + '" r="64" fill="none" stroke="rgba(255,59,92,0.35)" stroke-width="1" stroke-dasharray="3 4"/>';
      b += t(CX, CY - 12, "顶上事件", { anchor: "middle", size: 9.5, fill: "#ff8fa3", mono: 1 }) + t(CX, CY + 6, "两船碰撞", { anchor: "middle", size: 15, fill: "#fff", weight: 700 }) + t(CX, CY + 23, "Lily × Mary", { anchor: "middle", size: 10, fill: C.sec, mono: 1 });
      b += t(14, 22, "威胁 THREATS → 预防屏障", { size: 10, fill: C.muted, mono: 1 }) + t(W - 14, 22, "减缓屏障 → 后果 CONSEQUENCES", { anchor: "end", size: 10, fill: C.muted, mono: 1 });
      put("sy-bowtie-svg", svg(W, H, b));

      var W2 = 720, H2 = 214, b2 = '', LX = 104;
      var layers = ["政府 / 法规", "主管机关 / VTS", "公司 / 船东", "船舶 / 驾驶台", "设备与环境", "事件序列"];
      layers.forEach(function (ln, i) { var y = 4 + i * 35; b2 += r(2, y, W2 - 4, 32, i % 2 ? "rgba(20,36,60,0.35)" : "rgba(13,25,43,0.55)", null, 2) + t(10, y + 20, ln, { size: 10.5, fill: C.sec, weight: 600 }); });
      var nodes = { a: [0, 300, "雾航限速/单向通航规定缺位"], b: [1, 210, "VTS 未实施单向管制"], c: [1, 450, "航标配置不足"], d: [2, 160, "SMS 无雾航程序"], e: [2, 350, "船期考核压力"], f: [2, 540, "工休管理失效"], g: [3, 180, "船长未上驾驶台"], h: [3, 360, "BRM 失效"], i: [3, 560, "OOW 疲劳"], j: [4, 170, "ARPA 设置不当"], k: [4, 380, "能见度 1.5 nm"], m: [4, 560, "横流 1.2 kn"], n: [5, 200, "Mary 违规左转"], o: [5, 400, "碰撞"], p: [5, 590, "Lily 坐沉"] };
      var edges = [["a", "b"], ["b", "h"], ["c", "n"], ["d", "g"], ["e", "i"], ["f", "i"], ["g", "h"], ["i", "n"], ["h", "n"], ["j", "n"], ["k", "n"], ["m", "o"], ["n", "o"], ["o", "p"]];
      function npos(k) { var n = nodes[k]; return [LX + 20 + n[1] * 0.9, 4 + n[0] * 35 + 16]; }
      edges.forEach(function (e) { var p1 = npos(e[0]), p2 = npos(e[1]); if (p1[1] === p2[1]) b2 += arrow(p1[0] + 56, p1[1], p2[0] - 58, p2[1], "rgba(255,176,32,0.7)"); else b2 += arrow(p1[0], p1[1] + 11, p2[0], p2[1] - 11, "rgba(141,164,196,0.55)"); });
      Object.keys(nodes).forEach(function (k) { var p = npos(k), n = nodes[k], ev = n[0] === 5; var w = Math.max(84, n[2].length * 11 + 14); b2 += r(p[0] - w / 2, p[1] - 11, w, 22, ev ? "rgba(255,176,32,0.15)" : "rgba(6,18,31,0.95)", ev ? C.amber : C.line, 3) + t(p[0], p[1] + 4, n[2], { anchor: "middle", size: 10, fill: k === "o" ? C.red : "#fff" }); });
      put("sy-accimap-svg", svg(W2, H2, b2));
    }

    // ---------- 15 征求意见轮次 ----------
    function renderRounds() {
      var W = 360, H = 74, b = '', X0 = 14, X1 = 346;
      var pts = [[0, "v1 发出", "06-20", C.green], [0.24, "第1轮截止", "07-20", C.green], [0.42, "v2 发出", "08-05", C.green], [0.80, "第2轮截止", "09-04", C.amber], [1, "定稿", "—", C.muted]];
      var x = function (f) { return X0 + f * (X1 - X0); };
      b += r(x(0), 30, x(0.24) - x(0), 6, "rgba(16,185,129,0.5)", null, 3) + r(x(0.42), 30, x(0.80) - x(0.42), 6, "rgba(255,176,32,0.3)", null, 3) + l(X0, 33, X1, 33, C.grid, 1);
      b += r(x(0.42), 30, x(0.66) - x(0.42), 6, "rgba(255,176,32,0.8)", null, 3);
      b += l(x(0.66), 18, x(0.66), 46, C.cyan, 1.5) + t(x(0.66), 14, "今天 08-23", { anchor: "middle", size: 9.5, fill: C.cyan, weight: 700 });
      pts.forEach(function (p, i) { b += '<circle cx="' + x(p[0]) + '" cy="33" r="5" fill="#06121f" stroke="' + p[3] + '" stroke-width="2"/>' + t(x(p[0]), 58, p[1], { anchor: i === 0 ? "start" : i === pts.length - 1 ? "end" : "middle", size: 9.5, fill: C.text }) + t(x(p[0]), 70, p[2], { anchor: i === 0 ? "start" : i === pts.length - 1 ? "end" : "middle", size: 9, fill: C.muted, mono: 1 }); });
      b += t(x(0.12), 24, "30 天", { anchor: "middle", size: 9, fill: C.green, mono: 1 }) + t(x(0.88), 24, "", {});
      put("rc-round-svg", svg(W, H, b));
    }

    // ---------- 16 事故等级 ----------
    function renderLevel() {
      var W = 420, H = 54, b = '', segs = [["海上事件", "rgba(141,164,196,0.25)", C.sec], ["较轻事故", "rgba(16,185,129,0.25)", C.green], ["严重事故", "rgba(255,176,32,0.25)", C.amber], ["非常严重事故", "rgba(255,59,92,0.35)", C.red]];
      var sw = 100;
      segs.forEach(function (s, i) { var x0 = 8 + i * (sw + 2); b += r(x0, 22, sw, 24, s[1], i === 3 ? s[2] : null, 2, i === 3 ? ' stroke-width="2"' : '') + t(x0 + sw / 2, 38, s[0], { anchor: "middle", size: 11, fill: i === 3 ? "#fff" : s[2], weight: i === 3 ? 700 : 400 }); });
      var px = 8 + 3 * (sw + 2) + sw / 2;
      b += '<polygon points="' + (px - 6) + ',6 ' + (px + 6) + ',6 ' + px + ',17" fill="' + C.red + '"/>' + t(px - 12, 14, "判定结果", { anchor: "end", size: 10, fill: C.red, weight: 700 });
      put("kn-level-svg", svg(W, H, b));
    }

    // ---------- 17 审计 ----------
    function renderAudit() {
      var W = 420, H = 92, b = '', X0 = 30, rnd = seeded(5);
      b += t(4, 12, "近 14 天访问与导出（审计日志 audit/access.jsonl）", { size: 10, fill: C.muted });
      for (var d = 0; d < 14; d++) {
        var x0 = X0 + d * 27, v = 3 + Math.floor(rnd() * 9), e = d === 12 ? 2 : (rnd() > 0.75 ? 1 : 0), bl = d === 9 ? 1 : 0;
        var y = 76;
        b += r(x0, y - v * 4.5, 16, v * 4.5, "rgba(59,227,255,0.55)", null, 1);
        if (e) b += r(x0, y - v * 4.5 - e * 6, 16, e * 6, C.amber, null, 1);
        if (bl) b += r(x0, y - v * 4.5 - 7, 16, 6, C.red, null, 1);
        b += t(x0 + 8, 88, (d + 21 > 31 ? "06-0" + (d - 10) : "05-" + (d + 21)), { anchor: "middle", size: 7.5, fill: C.muted, mono: 1 });
      }
      b += l(X0 - 4, 76, W - 4, 76, C.grid, 1);
      b += r(W - 150, 5, 9, 7, "rgba(59,227,255,0.55)") + t(W - 138, 12, "访问", { size: 9, fill: C.sec }) + r(W - 105, 5, 9, 7, C.amber) + t(W - 93, 12, "导出", { size: 9, fill: C.sec }) + r(W - 60, 5, 9, 7, C.red) + t(W - 48, 12, "被拒绝", { size: 9, fill: C.sec });
      put("ac-audit-svg", svg(W, H, b));
    }

    function renderDist() {
      var W = 700, H = 58, b = '', items = [["瞭望不足 R5", 17, C.red], ["安全航速 R6/R19", 14, C.red], ["BRM 失效", 12, C.amber], ["疲劳", 9, C.amber], ["VTS 组织", 7, C.cyan], ["SMS 程序缺失", 6, C.purple]];
      var bw = 112;
      items.forEach(function (it, i) { var x0 = 4 + i * (bw + 3); b += t(x0, 14, it[0], { size: 10, fill: C.text }) + r(x0, 22, bw - 6, 10, "rgba(141,164,196,0.12)", null, 2) + r(x0, 22, (bw - 6) * it[1] / 20, 10, it[2], null, 2) + t(x0, 48, it[1] + " / 20", { size: 9.5, fill: C.muted, mono: 1 }); });
      put("kn-dist-svg", svg(W, H, b));
    }
    renderDist();
    renderVdr(); renderClock(); renderIvTimeline(); renderColreg(); renderWhatif(); renderHf(); renderSystemic(); renderRounds(); renderLevel(); renderAudit();
  })();
  </script>
