(function () {
  "use strict";

  function normalizeText(value) {
    return String(value || "")
      .toLocaleLowerCase("id-ID")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function isUsefulTable(table) {
    if (!table || table.dataset.globalSearch === "off") return false;
    if (table.closest(".django-admin, #changelist")) return false;

    var tbody = table.tBodies && table.tBodies[0];
    if (!tbody) return false;

    var rows = Array.from(tbody.rows).filter(function (row) {
      return !row.querySelector("td[colspan]");
    });

    return rows.length > 0;
  }

  function createToolbar(table, index) {
    var toolbar = document.createElement("div");
    toolbar.className = "global-data-search";
    toolbar.dataset.searchFor = "global-table-" + index;

    var inputId = "global-data-search-input-" + index;

    toolbar.innerHTML =
      '<div class="global-data-search__field">' +
        '<label class="visually-hidden" for="' + inputId + '">Cari data</label>' +
        '<i class="fa-solid fa-magnifying-glass global-data-search__icon" aria-hidden="true"></i>' +
        '<input type="search" id="' + inputId + '" class="form-control global-data-search__input" ' +
          'placeholder="Cari data pada tabel ini..." autocomplete="off">' +
        '<button type="button" class="global-data-search__clear" aria-label="Hapus pencarian" title="Hapus pencarian">' +
          '<i class="fa-solid fa-xmark" aria-hidden="true"></i>' +
        '</button>' +
      '</div>' +
      '<div class="global-data-search__meta" aria-live="polite"></div>';

    var wrapper = table.closest(".table-responsive");
    var insertionTarget = wrapper || table;
    insertionTarget.parentNode.insertBefore(toolbar, insertionTarget);

    return toolbar;
  }

  function installTableSearch(table, index) {
    if (!isUsefulTable(table) || table.dataset.globalSearchReady === "1") return;

    table.dataset.globalSearchReady = "1";
    table.id = table.id || "global-table-" + index;

    var toolbar = createToolbar(table, index);
    var input = toolbar.querySelector(".global-data-search__input");
    var clearButton = toolbar.querySelector(".global-data-search__clear");
    var meta = toolbar.querySelector(".global-data-search__meta");
    var tbody = table.tBodies[0];

    var rows = Array.from(tbody.rows);
    var searchableRows = rows.filter(function (row) {
      return !row.querySelector("td[colspan]");
    });
    var emptyRows = rows.filter(function (row) {
      return !!row.querySelector("td[colspan]");
    });

    searchableRows.forEach(function (row) {
      row.dataset.searchText = normalizeText(row.innerText);
    });

    var noResultRow = document.createElement("tr");
    noResultRow.className = "global-data-search__empty";
    noResultRow.hidden = true;

    var emptyCell = document.createElement("td");
    emptyCell.colSpan = Math.max(table.rows[0] ? table.rows[0].cells.length : 1, 1);
    emptyCell.className = "text-center text-muted py-4";
    emptyCell.textContent = "Tidak ada data yang cocok dengan pencarian.";
    noResultRow.appendChild(emptyCell);
    tbody.appendChild(noResultRow);

    function update() {
      var keyword = normalizeText(input.value);
      var visible = 0;

      searchableRows.forEach(function (row) {
        var matched = !keyword || row.dataset.searchText.indexOf(keyword) !== -1;
        row.hidden = !matched;
        if (matched) visible += 1;
      });

      emptyRows.forEach(function (row) {
        row.hidden = !!keyword;
      });

      noResultRow.hidden = !keyword || visible > 0;
      clearButton.classList.toggle("is-visible", !!keyword);

      if (keyword) {
        meta.textContent = visible + " dari " + searchableRows.length + " data pada halaman ini";
      } else {
        meta.textContent = searchableRows.length + " data pada halaman ini";
      }
    }

    var timer = null;
    input.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(update, 180);
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        input.value = "";
        update();
        input.blur();
      }
    });

    clearButton.addEventListener("click", function () {
      input.value = "";
      update();
      input.focus();
    });

    update();
  }

  function installAll() {
    Array.from(document.querySelectorAll("table")).forEach(function (table, index) {
      installTableSearch(table, index + 1);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", installAll);
  } else {
    installAll();
  }
})();
