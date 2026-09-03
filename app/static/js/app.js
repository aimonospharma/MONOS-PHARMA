/* MP team — нийтлэг UI зан төлөв */
(function () {
  "use strict";

  /* ---------------------------------------------- count-up animation */
  function countUp(el) {
    const target = parseFloat(el.dataset.count || "0");
    const decimals = parseInt(el.dataset.decimals || "0", 10);
    const suffix = el.dataset.suffix || "";
    const dur = 900;
    const start = performance.now();
    function frame(t) {
      const p = Math.min((t - start) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = target * eased;
      el.textContent = (decimals
        ? val.toFixed(decimals)
        : Math.round(val).toLocaleString("en-US").replace(/,/g, " ")) + suffix;
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  const io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { countUp(e.target); io.unobserve(e.target); }
    });
  }, { threshold: 0.35 });

  document.querySelectorAll("[data-count]").forEach(function (el) { io.observe(el); });

  /* --------------------------------------------------- progress bars */
  document.querySelectorAll(".progress > i[data-width]").forEach(function (el) {
    setTimeout(function () { el.style.width = el.dataset.width + "%"; }, 120);
  });

  /* ------------------------------------------------- mobile sidebar */
  const sidebar = document.querySelector(".sidebar");
  const burger = document.querySelector(".burger");
  if (burger && sidebar) {
    burger.addEventListener("click", function () {
      sidebar.classList.toggle("open");
      let scrim = document.querySelector(".scrim");
      if (sidebar.classList.contains("open")) {
        scrim = document.createElement("div");
        scrim.className = "scrim";
        scrim.addEventListener("click", function () {
          sidebar.classList.remove("open");
          scrim.remove();
        });
        document.body.appendChild(scrim);
      } else if (scrim) { scrim.remove(); }
    });
  }

  /* ------------------------------------------------ auto-submit форм */
  document.querySelectorAll("[data-autosubmit]").forEach(function (el) {
    el.addEventListener("change", function () { el.form.submit(); });
  });

  /* --------------------------------------------- checkbox card стиль */
  document.querySelectorAll(".check input[type=checkbox]").forEach(function (cb) {
    const sync = function () { cb.closest(".check").classList.toggle("checked", cb.checked); };
    cb.addEventListener("change", sync);
    sync();
  });

  /* ------------------------------------------------- drag&drop upload */
  document.querySelectorAll("[data-dropzone]").forEach(function (zone) {
    const input = document.getElementById(zone.dataset.dropzone);
    const info = zone.parentElement.querySelector("[data-fileinfo]");
    const preview = zone.parentElement.querySelector("[data-preview]");
    if (!input) return;

    function show(file) {
      if (!file) return;
      if (info) {
        info.hidden = false;
        info.innerHTML =
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">' +
          '<path d="M20 6 9 17l-5-5"/></svg><b>' + file.name + "</b>" +
          '<span class="dim small">' + (file.size / 1048576).toFixed(1) + " MB</span>";
      }
      if (preview) {
        preview.innerHTML = "";
        const url = URL.createObjectURL(file);
        if (file.type.startsWith("video")) {
          const v = document.createElement("video");
          v.src = url; v.controls = true; preview.appendChild(v);
        } else if (file.type.startsWith("image")) {
          const i = document.createElement("img");
          i.src = url; preview.appendChild(i);
        } else {
          preview.innerHTML = '<span class="dim small">Preview боломжгүй файл (' + file.type + ")</span>";
        }
        preview.hidden = false;
      }
    }

    zone.addEventListener("click", function () { input.click(); });
    input.addEventListener("change", function () { show(input.files[0]); });
    ["dragenter", "dragover"].forEach(function (ev) {
      zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.add("drag"); });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.remove("drag"); });
    });
    zone.addEventListener("drop", function (e) {
      const files = e.dataTransfer.files;
      if (files && files.length) { input.files = files; show(files[0]); }
    });
  });

  /* ------------------------------------------ видео үзэлтийн явц бичих */
  const player = document.querySelector("video[data-view-id]");
  if (player) {
    const viewId = player.dataset.viewId;
    let last = 0;
    const send = function (completed) {
      const watched = Math.round(player.currentTime);
      if (!completed && watched - last < 10) return;
      last = watched;
      fetch("/api/view/" + viewId + "/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ watched: watched, completed: !!completed }),
        keepalive: true,
      }).catch(function () {});
    };
    player.addEventListener("timeupdate", function () { send(false); });
    player.addEventListener("ended", function () { send(true); });
    window.addEventListener("beforeunload", function () { send(false); });
  }

  /* --------------------------------- зураг/постерын үзэлтийн хугацаа */
  const still = document.querySelector("[data-still-view]");
  if (still) {
    const viewId = still.dataset.stillView;
    const t0 = Date.now();
    window.addEventListener("beforeunload", function () {
      const sec = Math.round((Date.now() - t0) / 1000);
      if (sec < 3) return;
      navigator.sendBeacon(
        "/api/view/" + viewId + "/progress",
        new Blob([JSON.stringify({ watched: sec, completed: sec > 10 })], { type: "application/json" })
      );
    });
  }

  /* ------------------------------------------------ баталгаажуулалт */
  document.querySelectorAll("[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.dataset.confirm)) e.preventDefault();
    });
  });

  /* ---------------------------------------------------- copy to clip */
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      navigator.clipboard.writeText(btn.dataset.copy).then(function () {
        const old = btn.textContent;
        btn.textContent = "Хуулагдлаа ✓";
        setTimeout(function () { btn.textContent = old; }, 1600);
      });
    });
  });

  /* ------------------------------------------ бүх channel сонгох товч */
  const selectAll = document.querySelector("[data-select-all]");
  if (selectAll) {
    selectAll.addEventListener("click", function () {
      const boxes = document.querySelectorAll('input[name="channel_ids"]');
      const turnOn = Array.from(boxes).some(function (b) { return !b.checked; });
      boxes.forEach(function (b) {
        b.checked = turnOn;
        b.dispatchEvent(new Event("change"));
      });
      selectAll.textContent = turnOn ? "Сонголтыг цуцлах" : "Бүгдийг сонгох";
    });
  }
})();
