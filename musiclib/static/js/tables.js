function getCellValue(row, index) {
  const cell = row.children[index];
  if (!cell) return "";

  const sortValue = cell.getAttribute("data-sort");
  if (sortValue !== null) return sortValue;
  return cell.innerText.trim();
}

function compareValues(a, b) {
  const na = Number(a);
  const nb = Number(b);
  const aIsNum = !Number.isNaN(na) && a !== "";
  const bIsNum = !Number.isNaN(nb) && b !== "";

  if (aIsNum && bIsNum) return na - nb;
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
}

function makeSortable(table) {
  const thead = table.querySelector("thead");
  const tbody = table.querySelector("tbody");
  if (!thead || !tbody) return;

  const headers = Array.from(thead.querySelectorAll("th"));

  headers.forEach((th, idx) => {
    th.addEventListener("click", () => {
      const current = th.getAttribute("data-sort-dir") || "none";
      const dir = current === "asc" ? "desc" : "asc";

      headers.forEach((h) => h.removeAttribute("data-sort-dir"));
      th.setAttribute("data-sort-dir", dir);

      const rows = Array.from(tbody.querySelectorAll("tr"));
      rows.sort((ra, rb) => {
        const va = getCellValue(ra, idx);
        const vb = getCellValue(rb, idx);
        const cmp = compareValues(va, vb);
        return dir === "asc" ? cmp : -cmp;
      });

      rows.forEach((r) => tbody.appendChild(r));
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("table.sortable").forEach(makeSortable);
});
