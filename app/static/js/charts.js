/* MP team — Chart.js график тохиргоо (dark / neon) */
(function () {
  "use strict";
  if (typeof Chart === "undefined") return;

  const BRAND = "#00e0a4", CYAN = "#17d1ff", VIOLET = "#8b5cf6",
        PINK = "#ff4d94", AMBER = "#ffb020";

  Chart.defaults.color = "#94a2c6";
  Chart.defaults.font.family = '"Segoe UI", Inter, system-ui, sans-serif';
  Chart.defaults.font.size = 11.5;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.boxWidth = 8;
  Chart.defaults.plugins.legend.labels.padding = 14;
  Chart.defaults.plugins.tooltip.backgroundColor = "rgba(12,16,34,.95)";
  Chart.defaults.plugins.tooltip.borderColor = "rgba(255,255,255,.16)";
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 11;
  Chart.defaults.plugins.tooltip.cornerRadius = 10;
  Chart.defaults.plugins.tooltip.titleColor = "#eaf0ff";
  Chart.defaults.maintainAspectRatio = false;

  const GRID = { color: "rgba(255,255,255,.06)", drawTicks: false };
  const NO_GRID = { display: false };

  function fade(ctx, hex, top, bottom) {
    const g = ctx.createLinearGradient(0, 0, 0, 280);
    g.addColorStop(0, hex + top);
    g.addColorStop(1, hex + bottom);
    return g;
  }

  function shortDate(iso) {
    const p = String(iso).split("-");
    return p.length === 3 ? p[1] + "/" + p[2] : iso;
  }

  function mount(id) {
    const el = document.getElementById(id);
    return el ? el.getContext("2d") : null;
  }

  const node = document.getElementById("chart-data");
  if (!node) return;
  const D = JSON.parse(node.textContent);

  /* ------------------------------------------------- 1. Трэнд (line) */
  let ctx = mount("chartTrend");
  if (ctx && D.trend) {
    new Chart(ctx, {
      type: "line",
      data: {
        labels: D.trend.labels.map(shortDate),
        datasets: [
          { label: "Нийт үзэлт", data: D.trend.views, borderColor: BRAND,
            backgroundColor: fade(ctx, "#00e0a4", "44", "00"), fill: true,
            tension: .38, borderWidth: 2.4, pointRadius: 0, pointHoverRadius: 5,
            pointHoverBackgroundColor: BRAND },
          { label: "Үзсэн хүн (unique)", data: D.trend.viewers, borderColor: VIOLET,
            backgroundColor: "transparent", borderDash: [5, 4], fill: false,
            tension: .38, borderWidth: 2, pointRadius: 0, pointHoverRadius: 5 },
        ],
      },
      options: {
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: NO_GRID, ticks: { maxTicksLimit: 10 } },
          y: { grid: GRID, beginAtZero: true, ticks: { precision: 0 } },
        },
      },
    });
  }

  /* --------------------------------------- 2. Бүтээгдэхүүн (bar, h) */
  ctx = mount("chartProduct");
  if (ctx && D.product) {
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: D.product.labels,
        datasets: [{
          label: "Үзэлт", data: D.product.views,
          backgroundColor: D.product.colors.map(function (c) { return c + "cc"; }),
          borderColor: D.product.colors, borderWidth: 1.5,
          borderRadius: 7, borderSkipped: false, maxBarThickness: 26,
        }],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: { x: { grid: GRID, beginAtZero: true }, y: { grid: NO_GRID } },
      },
    });
  }

  /* --------------------------------------------- 3. Хэсэг (doughnut) */
  ctx = mount("chartSection");
  if (ctx && D.section) {
    new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: D.section.labels,
        datasets: [{
          data: D.section.views,
          backgroundColor: [AMBER + "dd", CYAN + "dd", VIOLET + "dd", PINK + "dd"],
          borderColor: "rgba(10,13,28,.9)", borderWidth: 3, hoverOffset: 10,
        }],
      },
      options: { cutout: "63%", plugins: { legend: { position: "bottom" } } },
    });
  }

  /* --------------------------------------------- 4. Channel (bar, v) */
  ctx = mount("chartChannel");
  if (ctx && D.channel) {
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: D.channel.labels,
        datasets: [{
          label: "Үзэлт", data: D.channel.views,
          backgroundColor: fade(ctx, "#17d1ff", "e0", "22"),
          borderRadius: 8, borderSkipped: false, maxBarThickness: 42,
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: NO_GRID, ticks: { callback: function (v) {
            const s = this.getLabelForValue(v); return s.length > 16 ? s.slice(0, 15) + "…" : s;
          } } },
          y: { grid: GRID, beginAtZero: true },
        },
      },
    });
  }

  /* -------------------------------------------- 5. Цагийн идэвх (bar) */
  ctx = mount("chartHourly");
  if (ctx && D.hourly) {
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: D.hourly.labels,
        datasets: [{
          label: "Үзэлт", data: D.hourly.views,
          backgroundColor: fade(ctx, "#8b5cf6", "e6", "1a"),
          borderRadius: 5, borderSkipped: false,
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { x: { grid: NO_GRID, ticks: { maxTicksLimit: 12 } }, y: { grid: GRID, beginAtZero: true } },
      },
    });
  }

  /* ------------------------------- 6. Хэрэглэгч × бүтээгдэхүүн матриц */
  const box = document.getElementById("matrixBox");
  if (box && D.matrix && D.matrix.rows.length) {
    const m = D.matrix;
    const max = Math.max.apply(null, m.rows.flatMap(function (r) { return r.cells; }).concat([1]));
    let html = '<div class="table-wrap"><table><thead><tr><th>Хэрэглэгч</th>';
    m.products.forEach(function (p, i) {
      html += '<th class="num"><span class="dot" style="display:inline-block;background:' +
        (m.colors[i] || "#7c5cff") + '"></span> ' + p + "</th>";
    });
    html += "</tr></thead><tbody>";
    m.rows.forEach(function (row) {
      html += "<tr><td><b>" + row.user + "</b></td>";
      row.cells.forEach(function (c, i) {
        const a = c / max;
        const color = m.colors[i] || "#7c5cff";
        html += '<td class="num"><span class="matrix-cell" style="background:' + color +
          Math.round(18 + a * 200).toString(16).padStart(2, "0") +
          ';color:' + (a > .55 ? "#06101c" : "#eaf0ff") + '">' + c + "</span></td>";
      });
      html += "</tr>";
    });
    box.innerHTML = html + "</tbody></table></div>";
  }

  /* ------------------------------------------ Profile: хувийн идэвх */
  ctx = mount("chartMe");
  if (ctx && D.labels && D.views) {
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: D.labels.map(shortDate),
        datasets: [{
          label: "Миний үзэлт", data: D.views,
          backgroundColor: fade(ctx, "#00e0a4", "e6", "22"),
          borderRadius: 5, borderSkipped: false,
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { x: { grid: NO_GRID, ticks: { maxTicksLimit: 10 } },
                  y: { grid: GRID, beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }
})();
