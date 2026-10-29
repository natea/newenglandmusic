// the town filter as chips (core/templates/core/geo_filter_form.html): the plain multi-select,
// which works without js but needs cmd-click for a second town, becomes an "add a town" list
// beside the chosen towns, each a chip with an x to remove it. the multi-select stays in the
// form, hidden, and is what's submitted: adding or removing a town changes it, and the form's
// own change handler submits.
document.querySelectorAll('form.geoFilter select[name="town"][multiple]').forEach(function (select) {
  const box = document.createElement("span");
  box.className = "town-chips";

  const add = document.createElement("select");
  add.className = "town-add";
  add.setAttribute("aria-label", "add a town");
  const prompt = document.createElement("option");
  prompt.value = "";
  prompt.textContent = select.selectedOptions.length ? "add another town" : "add a town";
  add.appendChild(prompt);

  [...select.options].forEach(function (option) {
    if (option.selected) {
      const chip = document.createElement("span");
      chip.className = "town-chip";
      chip.textContent = option.textContent;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "town-remove";
      remove.textContent = "×";
      remove.title = "Remove " + option.textContent;
      remove.setAttribute("aria-label", "Remove " + option.textContent);
      remove.addEventListener("click", function () {
        option.selected = false;
        select.dispatchEvent(new Event("change", { bubbles: true }));
      });
      chip.appendChild(remove);
      box.appendChild(chip);
    } else {
      const choice = document.createElement("option");
      choice.value = option.value;
      choice.textContent = option.textContent;
      add.appendChild(choice);
    }
  });

  // picking a town marks it in the hidden multi-select; the change then bubbles to the
  // form, which submits
  add.addEventListener("change", function () {
    const option = [...select.options].find(function (o) { return o.value === add.value; });
    if (option) {
      option.selected = true;
    }
  });

  select.hidden = true;
  select.style.display = "none";
  const label = select.closest("label");
  (label || select).after(box);
  if (add.options.length > 1) {
    box.appendChild(add);
  }
});
