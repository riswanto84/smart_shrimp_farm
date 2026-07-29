(function () {
  "use strict";

  function usefulTable(table) {
    if (!table || table.dataset.globalSearch === "off") return false;
    if (table.closest(".django-admin, #changelist")) return false;
    var tbody = table.tBodies && table.tBodies[0];
    if (!tbody) return false;
    return Array.from(tbody.rows).some(function (row) {
      return !row.querySelector("td[colspan]");
    });
  }

  function pageIsPaginated() {
    return !!document.querySelector(".pagination, nav[aria-label*='pagination' i], .page-item");
  }

  function preserveParams(form) {
    var current = new URL(window.location.href);
    current.searchParams.forEach(function (value, key) {
      if (key === "q" || key === "page") return;
      var hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = key;
      hidden.value = value;
      form.appendChild(hidden);
    });
  }

  function makeToolbar(table, index) {
    var old = table.parentElement && table.parentElement.previousElementSibling;
    if (old && old.classList && old.classList.contains("global-data-search")) old.remove();

    var form = document.createElement("form");
    form.className = "global-data-search";
    form.method = "get";
    form.action = window.location.pathname;
    form.setAttribute("role", "search");
    preserveParams(form);

    var inputId = "global-data-search-input-" + index;
    var keyword = new URL(window.location.href).searchParams.get("q") || "";
    form.innerHTML +=
      '<div class="global-data-search__field">' +
        '<label class="visually-hidden" for="' + inputId + '">Cari seluruh data</label>' +
        '<i class="fa-solid fa-magnifying-glass global-data-search__icon" aria-hidden="true"></i>' +
        '<input type="search" name="q" id="' + inputId + '" class="form-control global-data-search__input" ' +
          'placeholder="Masukkan kata pencarian..." autocomplete="off" value="' + keyword.replace(/&/g,"&amp;").replace(/"/g,"&quot;") + '">' +
      '</div>' +
      '<button type="submit" class="btn btn-primary global-data-search__submit">' +
        '<i class="fa-solid fa-magnifying-glass"></i> Cari' +
      '</button>' +
      '<button type="button" class="btn btn-outline-secondary global-data-search__reset">' +
        '<i class="fa-solid fa-rotate-left"></i> Reset' +
      '</button>' +
      '<div class="global-data-search__meta" aria-live="polite"></div>';

    var wrapper = table.closest(".table-responsive");
    var target = wrapper || table;
    target.parentNode.insertBefore(form, target);

    var rows = Array.from(table.tBodies[0].rows).filter(function (row) {
      return !row.querySelector("td[colspan]");
    });
    var meta = form.querySelector(".global-data-search__meta");
    meta.textContent = keyword
      ? rows.length + " hasil pada halaman ini · pencarian dilakukan ke seluruh database"
      : rows.length + " data pada halaman ini";

    form.querySelector(".global-data-search__reset").addEventListener("click", function () {
      var url = new URL(window.location.href);
      url.searchParams.delete("q");
      url.searchParams.delete("page");
      window.location.assign(url.toString());
    });

    // Untuk tabel tanpa pagination, seluruh data memang sudah ada di halaman.
    // Pencarian lokal hanya dipakai sebagai fallback untuk halaman seperti itu.
    if (!pageIsPaginated()) {
      form.addEventListener("submit", function (event) {
        var input = form.querySelector("input[name='q']");
        if (!input.value.trim()) return;
        // Tetap submit ke server bila view mendukung q; fallback lokal dilakukan
        // hanya bila halaman menandai tabel secara eksplisit.
        if (table.dataset.searchMode !== "client") return;
        event.preventDefault();
        var term = input.value.trim().toLowerCase();
        var found = 0;
        rows.forEach(function (row) {
          var match = row.textContent.toLowerCase().indexOf(term) !== -1;
          row.hidden = !match;
          if (match) found += 1;
        });
        meta.textContent = found + " data ditemukan";
      });
    }
  }

  function install() {
    Array.from(document.querySelectorAll("table")).forEach(function (table, index) {
      if (!usefulTable(table) || table.dataset.globalSearchReady === "2") return;
      table.dataset.globalSearchReady = "2";
      makeToolbar(table, index + 1);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install);
  else install();
})();
