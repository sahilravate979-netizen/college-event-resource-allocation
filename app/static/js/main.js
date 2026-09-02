function bindResourceRow(row) {
  const select = row.querySelector('select[name="resource_id[]"]');
  const hiddenType = row.querySelector('input[name="resource_type[]"]');
  if (select && hiddenType) {
    select.addEventListener("change", function () {
      const opt = select.options[select.selectedIndex];
      hiddenType.value = opt ? opt.getAttribute("data-type") || "" : "";
    });
  }
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".resource-row").forEach(bindResourceRow);

  const addBtn = document.getElementById("add-resource-row");
  const container = document.getElementById("resource-rows");

  if (addBtn && container) {
    addBtn.addEventListener("click", function () {
      const firstRow = container.querySelector(".resource-row");
      const newRow = firstRow.cloneNode(true);

      newRow.querySelectorAll("select").forEach((el) => (el.selectedIndex = 0));
      newRow.querySelectorAll('input[type="number"]').forEach((el) => (el.value = 1));
      newRow.querySelectorAll('input[type="hidden"]').forEach((el) => (el.value = ""));

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.textContent = "✕";
      removeBtn.className = "text-red-500 px-2";
      removeBtn.addEventListener("click", function () {
        newRow.remove();
      });

      newRow.appendChild(removeBtn);
      container.appendChild(newRow);
      bindResourceRow(newRow);
    });
  }
});
