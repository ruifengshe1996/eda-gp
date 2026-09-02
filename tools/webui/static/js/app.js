/* EDA-GP webUI front-end logic: markdown+KaTeX rendering, lightbox,
 * slice viewer, log-curve charts (Chart.js), git diff viewer. */
"use strict";

/* ------------------------------------------------------------------ *
 * markdown + KaTeX
 * ------------------------------------------------------------------ */

// Protect $...$ / $$...$$ spans from marked's emphasis/escape handling,
// restore them (HTML-escaped) after parsing, then let KaTeX auto-render
// pick the delimiters back up from the text nodes.
function renderMarkdown(el, src, baseDir) {
  const store = [];
  const stash = (m) => {
    store.push(m);
    return "K" + (store.length - 1) + "K";
  };
  let txt = src.replace(/\$\$[\s\S]+?\$\$/g, stash);
  txt = txt.replace(/\$(?=\S)([^$\n]*?\S)\$/g, stash);

  let html;
  try {
    html = marked.parse(txt, { gfm: true, mangle: false, headerIds: false });
  } catch (e) {
    el.textContent = src;
    return;
  }
  html = html.replace(/K(\d+)K/g, (_, i) => escapeHtml(store[+i]));
  el.innerHTML = html;

  // rewrite relative image/link paths against the markdown file location
  if (baseDir) {
    el.querySelectorAll("img").forEach((img) => {
      const s = img.getAttribute("src") || "";
      if (s && !/^(https?:)?\/|^data:/.test(s)) {
        img.src = "/img/" + encodePath(baseDir + "/" + s);
        img.classList.add("zoomable");
        img.loading = "lazy";
      }
    });
  }
  if (window.renderMathInElement) {
    renderMathInElement(el, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
    });
  }
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function encodePath(p) {
  return p.split("/").map(encodeURIComponent).join("/");
}

function fetchAndRenderMd(el) {
  const rel = el.dataset.md;
  fetch("/raw?p=" + encodeURIComponent(rel))
    .then((r) => {
      if (!r.ok) throw new Error(r.status);
      return r.text();
    })
    .then((txt) => {
      const baseDir = rel.includes("/") ? rel.slice(0, rel.lastIndexOf("/")) : "";
      renderMarkdown(el, txt, baseDir);
    })
    .catch(() => {
      el.innerHTML = '<p class="empty-hint">文件不存在或读取失败：' +
        escapeHtml(rel) + "</p>";
    });
}

/* ------------------------------------------------------------------ *
 * overlay: lightbox + slice viewer
 * ------------------------------------------------------------------ */

let overlayState = null; // {items: [{src, caption}], idx}

function ensureOverlay() {
  let ov = document.getElementById("overlay");
  if (ov) return ov;
  ov = document.createElement("div");
  ov.id = "overlay";
  ov.innerHTML =
    '<button class="ov-btn ov-close" title="关闭 (Esc)">×</button>' +
    '<button class="ov-btn ov-prev" title="上一张 (←)">‹</button>' +
    '<div class="ov-body"><img alt=""><div class="ov-caption"></div></div>' +
    '<button class="ov-btn ov-next" title="下一张 (→)">›</button>';
  document.body.appendChild(ov);
  ov.addEventListener("click", (e) => {
    if (e.target === ov || e.target.classList.contains("ov-close")) closeOverlay();
    else if (e.target.classList.contains("ov-prev")) stepOverlay(-1);
    else if (e.target.classList.contains("ov-next")) stepOverlay(1);
  });
  document.addEventListener("keydown", (e) => {
    if (!overlayState) return;
    if (e.key === "Escape") closeOverlay();
    else if (e.key === "ArrowLeft") stepOverlay(-1);
    else if (e.key === "ArrowRight") stepOverlay(1);
  });
  return ov;
}

function openOverlay(items, idx) {
  const ov = ensureOverlay();
  overlayState = { items, idx };
  ov.classList.toggle("multi", items.length > 1);
  updateOverlay();
  ov.classList.add("show");
}

function updateOverlay() {
  const ov = document.getElementById("overlay");
  const it = overlayState.items[overlayState.idx];
  ov.querySelector("img").src = it.src;
  ov.querySelector(".ov-caption").textContent =
    it.caption +
    (overlayState.items.length > 1
      ? "　(" + (overlayState.idx + 1) + "/" + overlayState.items.length + ")"
      : "");
}

function stepOverlay(d) {
  if (!overlayState || overlayState.items.length < 2) return;
  const n = overlayState.items.length;
  overlayState.idx = (overlayState.idx + d + n) % n;
  updateOverlay();
}

function closeOverlay() {
  const ov = document.getElementById("overlay");
  if (ov) ov.classList.remove("show");
  overlayState = null;
}

// simple lightbox: any .zoomable image opens alone
document.addEventListener("click", (e) => {
  const img = e.target.closest("img.zoomable");
  if (!img) return;
  e.preventDefault();
  openOverlay([{ src: img.src, caption: img.alt || "" }], 0);
});

/* ------------------------------------------------------------------ *
 * experiment page
 * ------------------------------------------------------------------ */

function initExpPage() {
  document.addEventListener("DOMContentLoaded", () => {
    // tabs
    document.querySelectorAll("#tabs .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("#tabs .tab").forEach((b) =>
          b.classList.toggle("active", b === btn));
        document.querySelectorAll(".tab-panel").forEach((p) =>
          p.classList.toggle("hidden", p.id !== "panel-" + btn.dataset.tab));
      });
    });

    // markdown blocks
    document.querySelectorAll("[data-md]").forEach(fetchAndRenderMd);
    const rs = document.getElementById("readme-results");
    if (rs && window.EXP.resultsSection) {
      renderMarkdown(rs, window.EXP.resultsSection,
        "experiments/" + window.EXP.name);
    }

    // slice viewer buttons
    document.querySelectorAll(".slice-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const g = (window.EXP.viz.groups || []).find(
          (x) => x.name === btn.dataset.gname);
        if (!g) return;
        const dsg = g.designs.find((x) => x.name === btn.dataset.design);
        if (!dsg) return;
        const items = dsg.slices.map((rel) => ({
          src: "/img/" + encodePath("experiments/" + window.EXP.name + "/" + rel),
          caption: dsg.name + " · " + rel.split("/").pop(),
        }));
        openOverlay(items, 0);
      });
    });

    // git commits: load lazily on first expand
    const box = document.getElementById("commits-box");
    if (box) {
      let loaded = false;
      box.addEventListener("toggle", () => {
        if (!box.open || loaded) return;
        loaded = true;
        loadCommits();
      });
    }

    loadCurves();
  });
}

/* ---------------- git commits + diffs ---------------- */

function colorizeDiff(diff) {
  return diff.split("\n").map((line) => {
    let cls = "d-ctx";
    if (/^diff --git/.test(line)) cls = "d-file";
    else if (/^(\+\+\+|---)/.test(line)) cls = "d-meta";
    else if (/^@@/.test(line)) cls = "d-hunk";
    else if (line.startsWith("+")) cls = "d-add";
    else if (line.startsWith("-")) cls = "d-del";
    return '<div class="d-line ' + cls + '">' +
      (escapeHtml(line) || "&nbsp;") + "</div>";
  }).join("");
}

function loadCommits() {
  const body = document.getElementById("commits-body");
  body.innerHTML = '<p class="loading">正在读取 git 历史…</p>';
  fetch("/api/exp/" + encodeURIComponent(window.EXP.name) + "/commits")
    .then((r) => r.json())
    .then((data) => {
      if (!data.commits || !data.commits.length) {
        body.innerHTML = '<p class="empty-hint">未找到触及该实验目录的提交。</p>';
        return;
      }
      body.innerHTML = "";
      data.commits.forEach((c) => {
        const det = document.createElement("details");
        det.className = "commit";
        const sum = document.createElement("summary");
        sum.innerHTML = '<code class="hash">' + escapeHtml(c.hash.slice(0, 8)) +
          "</code> <span class='cdate'>" + escapeHtml(c.date) + "</span> " +
          escapeHtml(c.subject);
        det.appendChild(sum);
        const inner = document.createElement("div");
        inner.className = "commit-body";
        let html = "";
        if (c.stat) {
          html += "<h4>改动统计</h4><pre class='stat'>" +
            escapeHtml(c.stat) + "</pre>";
        }
        if (c.diff) {
          html += "<h4>核心代码 diff（dreamplace-src/dreamplace/*.py, scripts/*.py）</h4>";
          if (c.diff_truncated) {
            html += "<p class='note'>diff 共 " + c.diff_total_lines +
              " 行，超过 800 行，已截断显示前 800 行。</p>";
          }
          html += "<div class='diff'>" + colorizeDiff(c.diff) + "</div>";
        } else {
          html += "<p class='note'>该提交未改动核心代码文件。</p>";
        }
        inner.innerHTML = html;
        det.appendChild(inner);
        body.appendChild(det);
      });
    })
    .catch(() => {
      body.innerHTML = '<p class="empty-hint">git 历史读取失败。</p>';
    });
}

/* ---------------- convergence curves ---------------- */

const CHART_COMMON = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  interaction: { mode: "nearest", intersect: false },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        title: (items) => "iteration " + (items[0] ? items[0].parsed.x : ""),
      },
    },
  },
  elements: { point: { radius: 0 }, line: { borderWidth: 1.4 } },
  scales: { x: { type: "linear", title: { display: true, text: "iteration" } } },
};

let charts = {};
let curveSeries = [];

function seriesColor(i, n) {
  const hue = Math.round((360 * i) / Math.max(n, 1));
  return "hsl(" + hue + ", 65%, 45%)";
}

let curvesWithRef = false;

function loadCurves() {
  const block = document.getElementById("curves-block");
  if (!block) return;
  const ctrl = document.getElementById("curves-controls");
  fetch("/api/exp/" + encodeURIComponent(window.EXP.name) + "/curves" +
        (curvesWithRef ? "?ref=1" : ""))
    .then((r) => r.json())
    .then((data) => {
      const prevDesign = document.getElementById("design-select");
      const keep = prevDesign ? prevDesign.value : null;
      curveSeries = data.series || [];
      if (!curveSeries.length) {
        block.innerHTML =
          '<p class="empty-hint">logs/ 下没有可解析出迭代序列的日志。</p>';
        return;
      }
      buildCurveControls(ctrl);
      if (keep) {
        const ds = document.getElementById("design-select");
        ds.value = keep;
        ds.dispatchEvent(new Event("change", { bubbles: true }));
      }
      redrawCharts();
    })
    .catch(() => {
      block.innerHTML = '<p class="empty-hint">日志解析接口调用失败。</p>';
    });
}

function seriesDesign(label) {
  const parts = label.split("/");
  return parts[parts.length - 1];
}

function buildCurveControls(ctrl) {
  // group series by variant prefix (label dirname), default-select the
  // series of the alphabetically first design so the chart starts readable
  const designs = [...new Set(curveSeries.map((s) => seriesDesign(s.label)))].sort();
  const defaultDesign = designs[0];
  const groups = {};
  curveSeries.forEach((s, i) => {
    const parts = s.label.split("/");
    const g = parts.length > 1 ? parts.slice(0, -1).join("/") : "（logs 根）";
    (groups[g] = groups[g] || []).push(i);
  });

  let html = '<div class="ctrl-row">'
    + '<span class="ctrl-label">按设计快速选择：</span>'
    + '<select id="design-select"><option value="">（手动勾选）</option>';
  designs.forEach((d) => {
    html += '<option value="' + escapeHtml(d) + '"'
      + (d === defaultDesign ? " selected" : "") + ">" + escapeHtml(d)
      + "</option>";
  });
  html += "</select>"
    + ' <button class="btn" id="sel-all">全选</button>'
    + ' <button class="btn" id="sel-none">全不选</button>'
    + ' <label class="ctrl-label"><input type="checkbox" id="log-scale" checked> wHPWL 对数刻度</label>'
    + ' <label class="ctrl-label"><input type="checkbox" id="with-ref"'
    + (curvesWithRef ? " checked" : "") + "> 叠加 center 基线（虚线）</label>"
    + "</div>";

  Object.keys(groups).sort().forEach((g) => {
    html += '<div class="ctrl-group"><span class="ctrl-group-name">'
      + escapeHtml(g) + "：</span>";
    groups[g].forEach((i) => {
      const s = curveSeries[i];
      const checked = seriesDesign(s.label) === defaultDesign ? " checked" : "";
      html += '<label class="series-chk' + (s.ref ? " ref" : "") + '" style="--c:' +
        seriesColor(i, curveSeries.length) + '">' +
        '<input type="checkbox" data-idx="' + i + '"' + checked + "> " +
        escapeHtml(seriesDesign(s.label)) + "</label>";
    });
    html += "</div>";
  });
  ctrl.innerHTML = html;

  ctrl.addEventListener("change", (e) => {
    if (e.target.id === "with-ref") {
      curvesWithRef = e.target.checked;
      loadCurves();
      return;
    }
    if (e.target.id === "design-select") {
      const d = e.target.value;
      if (d) {
        ctrl.querySelectorAll("input[data-idx]").forEach((cb) => {
          cb.checked = seriesDesign(curveSeries[+cb.dataset.idx].label) === d;
        });
      }
    }
    redrawCharts();
  });
  ctrl.querySelector("#sel-all").addEventListener("click", () => {
    ctrl.querySelectorAll("input[data-idx]").forEach((cb) => (cb.checked = true));
    ctrl.querySelector("#design-select").value = "";
    redrawCharts();
  });
  ctrl.querySelector("#sel-none").addEventListener("click", () => {
    ctrl.querySelectorAll("input[data-idx]").forEach((cb) => (cb.checked = false));
    ctrl.querySelector("#design-select").value = "";
    redrawCharts();
  });
}

function selectedIndices() {
  return [...document.querySelectorAll("#curves-controls input[data-idx]")]
    .filter((cb) => cb.checked)
    .map((cb) => +cb.dataset.idx);
}

function makeDatasets(indices, field) {
  return indices.map((i) => {
    const s = curveSeries[i];
    return {
      label: s.label,
      data: s.iter.map((x, k) => ({ x, y: s[field][k] })),
      borderColor: seriesColor(i, curveSeries.length),
      borderDash: s.ref ? [6, 4] : [],
      backgroundColor: "transparent",
    };
  });
}

function redrawCharts() {
  const idx = selectedIndices();
  const logScale = document.getElementById("log-scale");
  const useLog = !logScale || logScale.checked;

  const cfgs = [
    {
      id: "chart-whpwl", field: "whpwl", title: "wHPWL",
      yType: useLog ? "logarithmic" : "linear",
    },
    { id: "chart-overflow", field: "overflow", title: "Overflow", yType: "linear" },
  ];
  cfgs.forEach((c) => {
    const canvas = document.getElementById(c.id);
    if (!canvas) return;
    if (charts[c.id]) charts[c.id].destroy();
    const opts = JSON.parse(JSON.stringify(CHART_COMMON));
    opts.plugins.title = { display: true, text: c.title };
    opts.plugins.legend = { display: true, position: "bottom",
      labels: { boxWidth: 14, font: { size: 10 } } };
    opts.plugins.tooltip = CHART_COMMON.plugins.tooltip;
    opts.scales.y = { type: c.yType };
    charts[c.id] = new Chart(canvas, {
      type: "line",
      data: { datasets: makeDatasets(idx, c.field) },
      options: opts,
    });
  });
}

/* ------------------------------------------------------------------ *
 * docs page
 * ------------------------------------------------------------------ */

function initDocsPage() {
  document.addEventListener("DOMContentLoaded", () => {
    const nav = document.getElementById("docs-nav");
    const content = document.getElementById("doc-content");
    if (!nav || !content) return;

    function show(rel) {
      nav.querySelectorAll("a").forEach((a) =>
        a.classList.toggle("active", a.dataset.rel === rel));
      content.innerHTML = '<p class="loading">正在加载…</p>';
      fetch("/raw?p=" + encodeURIComponent(rel))
        .then((r) => {
          if (!r.ok) throw new Error(r.status);
          return r.text();
        })
        .then((txt) => {
          const baseDir = rel.includes("/")
            ? rel.slice(0, rel.lastIndexOf("/")) : "";
          renderMarkdown(content, txt, baseDir);
          content.scrollTop = 0;
        })
        .catch(() => {
          content.innerHTML = '<p class="empty-hint">文档读取失败：' +
            escapeHtml(rel) + "</p>";
        });
    }

    nav.querySelectorAll("a").forEach((a) => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        location.hash = a.dataset.rel;
        show(a.dataset.rel);
      });
    });

    const initial = decodeURIComponent(location.hash.slice(1));
    const first = nav.querySelector("a");
    if (initial && nav.querySelector('a[data-rel="' + CSS.escape(initial) + '"]')) {
      show(initial);
    } else if (first) {
      show(first.dataset.rel);
    }
  });
}

/* ------------------------------------------------------------------ *
 * index page: pick experiments to compare
 * ------------------------------------------------------------------ */

function initIndexPage() {
  document.addEventListener("DOMContentLoaded", () => {
    const KEY = "edagp.cmp.selected";
    let selected = new Set();
    try { selected = new Set(JSON.parse(sessionStorage.getItem(KEY) || "[]")); }
    catch (e) { selected = new Set(); }

    const boxes = [...document.querySelectorAll(".cmp-chk")];
    const count = document.getElementById("cmp-count");
    const go = document.getElementById("cmp-go");
    const clear = document.getElementById("cmp-clear");

    function sync() {
      boxes.forEach((cb) => {
        cb.checked = selected.has(cb.dataset.name);
        cb.closest(".card").classList.toggle("selected", cb.checked);
      });
      count.textContent = "已选 " + selected.size + " 个实验";
      go.disabled = selected.size === 0;
      try { sessionStorage.setItem(KEY, JSON.stringify([...selected])); }
      catch (e) { /* storage unavailable: selection is still kept in memory */ }
    }
    // the checkbox sits inside the card's <a>: swallow the navigation
    boxes.forEach((cb) => {
      cb.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const n = cb.dataset.name;
        if (selected.has(n)) selected.delete(n); else selected.add(n);
        sync();
      });
    });
    go.addEventListener("click", () => {
      if (!selected.size) return;
      location.href = "/compare?exps=" + encodeURIComponent([...selected].join(","));
    });
    clear.addEventListener("click", () => { selected.clear(); sync(); });
    sync();
  });
}

/* ------------------------------------------------------------------ *
 * compare page: table + overlaid curves across experiments
 * ------------------------------------------------------------------ */

const DESIGN_ORDER = ["adaptec1", "adaptec2", "adaptec3", "adaptec4",
                      "bigblue1", "bigblue2", "bigblue3", "bigblue4"];

function designSort(a, b) {
  const ia = DESIGN_ORDER.indexOf(a), ib = DESIGN_ORDER.indexOf(b);
  if (ia >= 0 && ib >= 0) return ia - ib;
  if (ia >= 0) return -1;
  if (ib >= 0) return 1;
  return a.localeCompare(b);
}

function geomeanPct(deltas) {
  if (!deltas.length) return null;
  const s = deltas.reduce((acc, d) => acc + Math.log(1 + d / 100), 0);
  return (Math.exp(s / deltas.length) - 1) * 100;
}

let cmpData = null;      // API payload
let cmpColumns = [];     // [{key, exp, group, label, metrics: {design: {whpwl, iters}}}]
let cmpSeries = [];      // flattened series with column index
let cmpCharts = {};

function initComparePage() {
  document.addEventListener("DOMContentLoaded", () => {
    const names = (window.CMP && window.CMP.names) || [];
    if (!names.length) return;
    fetch("/api/compare?exps=" + encodeURIComponent(names.join(",")))
      .then((r) => r.json())
      .then((data) => {
        cmpData = data;
        buildCompareColumns();
        buildCompareTable();
        buildCompareCurveControls();
        redrawCompareCharts();
      })
      .catch(() => {
        document.getElementById("cmp-table").innerHTML =
          '<p class="empty-hint">比较接口调用失败。</p>';
      });
  });
}

function buildCompareColumns() {
  cmpColumns = [];
  cmpSeries = [];
  // baseline first so it is the default reference
  const b = cmpData.baseline;
  if (b && Object.keys(b.metrics || {}).length) {
    cmpColumns.push({ key: "__baseline", exp: b.name, group: "",
      label: b.name + "（基线）", metrics: b.metrics, ref: true });
    (b.series || []).forEach((s) => cmpSeries.push({ ...s, col: 0 }));
  }
  cmpData.experiments.forEach((e) => {
    const groups = {};
    e.metrics.forEach((m) => {
      (groups[m.group] = groups[m.group] || {})[m.design] = m;
    });
    const gnames = Object.keys(groups).sort();
    if (!gnames.length) {
      // experiment with logs but no parseable final metrics: still show its curves
      const idx = cmpColumns.push({ key: e.name, exp: e.name, group: "",
        label: e.name, metrics: {} }) - 1;
      e.series.forEach((s) => cmpSeries.push({ ...s, col: idx }));
      return;
    }
    gnames.forEach((g) => {
      const idx = cmpColumns.push({ key: e.name + "/" + g, exp: e.name, group: g,
        label: e.name + (g ? " / " + g : ""), metrics: groups[g] }) - 1;
      e.series.forEach((s) => {
        const parts = s.label.split("/");
        const sg = parts.length > 1 ? parts.slice(0, -1).join("/") : "";
        if (sg === g) cmpSeries.push({ ...s, col: idx });
      });
    });
  });
}

function buildCompareTable() {
  const sel = document.getElementById("ref-select");
  sel.innerHTML = cmpColumns.map((c, i) =>
    '<option value="' + i + '">' + escapeHtml(c.label) + "</option>").join("");
  sel.addEventListener("change", renderCompareTable);
  document.getElementById("show-iters").addEventListener("change", renderCompareTable);
  renderCompareTable();
}

function renderCompareTable() {
  const refIdx = +document.getElementById("ref-select").value || 0;
  const showIters = document.getElementById("show-iters").checked;
  const ref = cmpColumns[refIdx];
  const designs = [...new Set(cmpColumns.flatMap((c) => Object.keys(c.metrics)))]
    .sort(designSort);
  let html = '<table class="data-table cmp-table"><thead><tr><th>design</th>';
  cmpColumns.forEach((c, i) => {
    html += '<th class="grp' + (i === refIdx ? " ref" : "") + '">' +
      escapeHtml(c.label) + "</th>";
  });
  html += "</tr></thead><tbody>";
  const deltas = cmpColumns.map(() => []);
  designs.forEach((d) => {
    html += "<tr><td>" + escapeHtml(d) + "</td>";
    const r = ref.metrics[d];
    cmpColumns.forEach((c, i) => {
      const m = c.metrics[d];
      if (!m) { html += '<td class="num">—</td>'; return; }
      let cell = (m.whpwl / 1e6).toFixed(2);
      let cls = "num";
      if (r && i !== refIdx) {
        const dlt = (m.whpwl / r.whpwl - 1) * 100;
        deltas[i].push(dlt);
        cell += " <small>(" + (dlt >= 0 ? "+" : "") + dlt.toFixed(2) + "%)</small>";
        cls += dlt > 0.05 ? " pos" : dlt < -0.05 ? " neg" : "";
      }
      if (i === refIdx) cls += " ref";
      if (showIters) cell += " <small>[" + m.iters + "]</small>";
      html += '<td class="' + cls + '">' + cell + "</td>";
    });
    html += "</tr>";
  });
  html += '<tr class="geo"><td>geomean Δ</td>';
  cmpColumns.forEach((c, i) => {
    if (i === refIdx) { html += '<td class="num ref">0</td>'; return; }
    const g = geomeanPct(deltas[i]);
    html += '<td class="num' + (g == null ? "" : g > 0 ? " pos" : " neg") + '">' +
      (g == null ? "—" : (g >= 0 ? "+" : "") + g.toFixed(2) + "% <small>(n=" +
       deltas[i].length + ")</small>") + "</td>";
  });
  html += "</tr></tbody></table>";
  document.getElementById("cmp-table").innerHTML = html;
}

function buildCompareCurveControls() {
  const ctrl = document.getElementById("cmp-controls");
  if (!cmpSeries.length) {
    document.getElementById("cmp-curves").innerHTML =
      '<p class="empty-hint">所选实验没有可解析的迭代日志。</p>';
    return;
  }
  const designs = [...new Set(cmpSeries.map((s) => seriesDesign(s.label)))].sort(designSort);
  let html = '<div class="ctrl-row"><span class="ctrl-label">设计：</span>'
    + '<select id="cmp-design">';
  designs.forEach((d, i) => {
    html += '<option value="' + escapeHtml(d) + '"' + (i === 0 ? " selected" : "") + ">" +
      escapeHtml(d) + "</option>";
  });
  html += "</select>"
    + ' <label class="ctrl-label"><input type="checkbox" id="cmp-log" checked> wHPWL 对数刻度</label>'
    + "</div>";
  html += '<div class="ctrl-group"><span class="ctrl-group-name">实验/变体：</span>';
  cmpColumns.forEach((c, i) => {
    html += '<label class="series-chk' + (c.ref ? " ref" : "") + '" style="--c:' +
      seriesColor(i, cmpColumns.length) + '"><input type="checkbox" data-col="' + i +
      '" checked> ' + escapeHtml(c.label) + "</label>";
  });
  html += "</div>";
  ctrl.innerHTML = html;
  ctrl.addEventListener("change", redrawCompareCharts);
}

function redrawCompareCharts() {
  const design = document.getElementById("cmp-design").value;
  const useLog = document.getElementById("cmp-log").checked;
  const cols = new Set([...document.querySelectorAll("#cmp-controls input[data-col]")]
    .filter((cb) => cb.checked).map((cb) => +cb.dataset.col));
  const picked = cmpSeries.filter((s) => cols.has(s.col) && seriesDesign(s.label) === design);
  const cfgs = [
    { id: "cmp-chart-whpwl", field: "whpwl", title: "wHPWL · " + design,
      yType: useLog ? "logarithmic" : "linear" },
    { id: "cmp-chart-overflow", field: "overflow", title: "Overflow · " + design,
      yType: "linear" },
  ];
  cfgs.forEach((c) => {
    const canvas = document.getElementById(c.id);
    if (!canvas) return;
    if (cmpCharts[c.id]) cmpCharts[c.id].destroy();
    const opts = JSON.parse(JSON.stringify(CHART_COMMON));
    opts.plugins.title = { display: true, text: c.title };
    opts.plugins.legend = { display: true, position: "bottom",
      labels: { boxWidth: 14, font: { size: 10 } } };
    opts.plugins.tooltip = CHART_COMMON.plugins.tooltip;
    opts.scales.y = { type: c.yType };
    cmpCharts[c.id] = new Chart(canvas, {
      type: "line",
      data: { datasets: picked.map((s) => ({
        label: cmpColumns[s.col].label,
        data: s.iter.map((x, k) => ({ x, y: s[c.field][k] })),
        borderColor: seriesColor(s.col, cmpColumns.length),
        borderDash: s.ref ? [6, 4] : [],
        backgroundColor: "transparent",
      })) },
      options: opts,
    });
  });
}
