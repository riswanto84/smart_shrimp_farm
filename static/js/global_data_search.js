(function () {
  "use strict";

  function isUsefulTable(table) {
    if (!table || table.dataset.globalSearch === "off") return false;
    if (table.closest(".django-admin, #changelist")) return false;
    var tbody = table.tBodies && table.tBodies[0];
    if (!tbody) return false;
    return Array.from(tbody.rows).some(function (row) {
      return !row.querySelector("td[colspan]");
    });
  }

  function createToolbar(table, index) {
    var toolbar = document.createElement("form");
    toolbar.className = "global-data-search";
    toolbar.setAttribute("role", "search");

    var inputId = "global-data-search-input-" + index;
    toolbar.innerHTML =
      '<div class="global-data-search__field">' +
        '<label class="visually-hidden" for="' + inputId + '">Cari data</label>' +
        '<i class="fa-solid fa-magnifying-glass global-data-search__icon" aria-hidden="true"></i>' +
        '<input type="search" id="' + inputId + '" class="form-control global-data-search__input" ' +
          'placeholder="Masukkan kata pencarian..." autocomplete="off">' +
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
    target.parentNode.insertBefore(toolbar, target);
    return toolbar;
  }

  function installTableSearch(table, index) {
    if (!isUsefulTable(table) || table.dataset.globalSearchReady === "1") return;
    table.dataset.globalSearchReady = "1";

    var toolbar = createToolbar(table, index);
    var input = toolbar.querySelector(".global-data-search__input");
    var resetButton = toolbar.querySelector(".global-data-search__reset");
    var meta = toolbar.querySelector(".global-data-search__meta");
    var rowsOnPage = Array.from(table.tBodies[0].rows).filter(function (row) {
      return !row.querySelector("td[colspan]");
    }).length;
    var url = new URL(window.location.href);
    var currentKeyword = url.searchParams.get("q") || "";

    input.value = currentKeyword;
    meta.textContent = currentKeyword
      ? rowsOnPage + " hasil pada halaman ini · pencarian seluruh database"
      : rowsOnPage + " data pada halaman ini";

    function navigate(keyword) {
      var nextUrl = new URL(window.location.href);
      if (keyword) nextUrl.searchParams.set("q", keyword);
      else nextUrl.searchParams.delete("q");
      nextUrl.searchParams.delete("page");
      window.location.assign(nextUrl.toString());
    }

    toolbar.addEventListener("submit", function (event) {
      event.preventDefault();
      navigate(input.value.trim());
    });

    resetButton.addEventListener("click", function () {
      navigate("");
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") navigate("");
    });
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
