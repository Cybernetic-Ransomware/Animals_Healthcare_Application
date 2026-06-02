// Sortable vaccination table. Called by tabs.js after every htmx swap.
// Uses a data-sortInit flag on the <table> element for idempotency:
//   - fresh table load (new DOM element) → no flag → init runs and attaches listeners
//   - row-level swap (same <table> element) → flag present → init returns early

function initVaccinationTable() {
    var table = document.getElementById("vaccination-table");
    if (!table || table.dataset.sortInit) return;
    table.dataset.sortInit = "1";

    table.querySelectorAll("thead th[data-sort]").forEach(function (th) {
        th.style.cursor = "pointer";
        th.style.userSelect = "none";
        th.addEventListener("click", function () {
            _sortVaccinationBy(table, th);
        });
    });

    var defaultTh = table.querySelector("thead th[data-default-sort]");
    if (defaultTh) {
        _sortVaccinationBy(table, defaultTh, defaultTh.dataset.defaultSort);
    }
}

function _sortVaccinationBy(table, th, forceDir) {
    var isAsc = forceDir ? forceDir === "asc" : th.dataset.dir !== "asc";

    table.querySelectorAll("thead th[data-sort]").forEach(function (h) {
        h.dataset.dir = "";
        h.textContent = h.dataset.label;
    });
    th.dataset.dir = isAsc ? "asc" : "desc";
    th.textContent = th.dataset.label + (isAsc ? " ▲" : " ▼");

    var tbody = table.querySelector("tbody");
    var colIdx = Array.from(table.querySelectorAll("thead th")).indexOf(th);
    var sortType = th.dataset.sort;

    var rows = Array.from(tbody.querySelectorAll("tr")).filter(function (row) {
        return !row.querySelector("input, button");
    });

    rows.sort(function (a, b) {
        var aCell = a.querySelectorAll("td")[colIdx];
        var bCell = b.querySelectorAll("td")[colIdx];
        if (!aCell || !bCell) return 0;

        var aVal = aCell.textContent.trim();
        var bVal = bCell.textContent.trim();

        if (sortType === "date") {
            var aTime = (aVal === "—" || aVal === "") ? null : new Date(aVal).getTime();
            var bTime = (bVal === "—" || bVal === "") ? null : new Date(bVal).getTime();
            if (aTime === null && bTime === null) return 0;
            if (aTime === null) return 1;
            if (bTime === null) return -1;
            return isAsc ? aTime - bTime : bTime - aTime;
        }

        return isAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });

    rows.forEach(function (row) { tbody.appendChild(row); });
}
