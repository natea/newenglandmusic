// "use my location" on the location form (core/templates/core/location_form.html): asks the
// browser for the device's position only when pressed, rounds it to three decimal places
// (about 100 m), and sends it to /location like a typed place. without js the button stays
// hidden, and typing a zip code or town still works.
document.querySelectorAll("form.locationForm .use-my-location").forEach(function (button) {
  if (!("geolocation" in navigator)) {
    return;
  }
  button.hidden = false;
  button.addEventListener("click", function () {
    const form = button.form;
    const next = form.querySelector('input[name="next"]').value;
    button.disabled = true;
    navigator.geolocation.getCurrentPosition(
      function (position) {
        const params = new URLSearchParams({
          lat: position.coords.latitude.toFixed(3),
          lon: position.coords.longitude.toFixed(3),
          next: next,
        });
        window.location.href = "/location?" + params.toString();
      },
      function () {
        window.location.href = "/location?" + new URLSearchParams({ error: "position", next: next }).toString();
      },
      { maximumAge: 600000, timeout: 15000 }
    );
  });
});

// suggestions as you type, in the browser's own list (the input's <datalist>): towns with
// venues on the site first, from /location/suggest. without js it's a plain text field
document.querySelectorAll('form.locationForm input[name="q"][list]').forEach(function (input) {
  const list = document.getElementById(input.getAttribute("list"));
  let timer = null;
  let asked = "";
  input.addEventListener("input", function () {
    clearTimeout(timer);
    const text = input.value.trim();
    if (text.length < 2) {
      list.replaceChildren();
      return;
    }
    timer = setTimeout(function () {
      if (text === asked) {
        return;
      }
      asked = text;
      fetch("/location/suggest?" + new URLSearchParams({ q: text }).toString())
        .then(function (response) { return response.ok ? response.json() : { suggestions: [] }; })
        .then(function (data) {
          if (input.value.trim() !== text) {
            return;
          }
          list.replaceChildren(...data.suggestions.map(function (label) {
            const option = document.createElement("option");
            option.value = label;
            return option;
          }));
        })
        .catch(function () {});
    }, 150);
  });
});
