// suggestions under the search box as you type (add-act-index-and-search): bands and artists,
// venues and upcoming shows from /search/suggest, each tagged with its kind, in GOV.UK's
// accessible-autocomplete (vendor/accessible-autocomplete), which does the keyboard and what
// screen readers announce. choosing a suggestion goes to its page; enter with none chosen runs
// the full search. without javascript the box stays the plain form it is in base.html.

(function () {
  const KIND_LABELS = { band: "Band", artist: "Artist", venue: "Venue", show: "Show" };
  const WAIT_MS = 150;

  function escape(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
  }

  // a character as matching sees it (core/search_marks.py): lowercase, no accents, letters and digits
  function fold(char) {
    return char.normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
  }

  // the name, escaped, with what was typed in <mark>, found as matching finds it
  function marked(text, query) {
    const wanted = Array.from(query || "").map(fold).join("");
    const chars = Array.from(text || "");
    const folded = [];
    const origin = [];
    chars.forEach(function (char, i) {
      Array.from(fold(char)).forEach(function (c) { folded.push(c); origin.push(i); });
    });
    const at = wanted ? folded.join("").indexOf(wanted) : -1;
    if (at < 0) return escape(text);
    const start = origin[at];
    const end = origin[at + wanted.length - 1] + 1;
    return escape(chars.slice(0, start).join("")) + "<mark>" + escape(chars.slice(start, end).join("")) +
      "</mark>" + escape(chars.slice(end).join(""));
  }

  let typed = "";

  // the suggestions for what's typed, debounced, each marked when it starts a new group
  function source() {
    let timer = null;
    let latest = 0;
    return function (query, populateResults) {
      clearTimeout(timer);
      typed = query;
      timer = setTimeout(function () {
        const asked = ++latest;
        fetch("/search/suggest?q=" + encodeURIComponent(query))
          .then(function (response) { return response.ok ? response.json() : { items: [] }; })
          .then(function (data) {
            // a slower answer to an earlier query mustn't replace a newer one
            if (asked !== latest) return;
            let group = null;
            populateResults(data.items.map(function (item) {
              const first = item.group !== group;
              group = item.group;
              return Object.assign({ first: first }, item);
            }));
          })
          .catch(function () { populateResults([]); });
      }, WAIT_MS);
    };
  }

  // a row: the group's label above the first of each group, then the kind tag, the name and a
  // quiet detail. those are hidden from screen readers, which hear "Belly, band, Providence, RI"
  function suggestion(item) {
    if (!item || typeof item === "string") return escape(item);
    const kind = KIND_LABELS[item.kind] || item.kind;
    const spoken = [item.name, kind.toLowerCase(), item.detail].filter(Boolean).join(", ");
    return (
      (item.first ? '<span class="suggest-group" aria-hidden="true">' + escape(item.group) + "</span>" : "") +
      '<span class="suggest-row" aria-hidden="true">' +
      '<span class="suggest-kind suggest-kind--' + escape(item.kind) + '">' + escape(kind) + "</span>" +
      '<span class="suggest-name">' + marked(item.name, typed) + "</span>" +
      (item.detail ? '<span class="suggest-detail">' + escape(item.detail) + "</span>" : "") +
      "</span>" +
      '<span class="suggest-spoken">' + escape(spoken) + "</span>"
    );
  }

  function mount(input, n) {
    const form = input.form;
    const container = document.createElement("div");
    container.className = "search-suggest";
    input.replaceWith(container);

    accessibleAutocomplete({
      element: container,
      // each box its own id, and keeps what was searched (the results page's box)
      id: n ? "search-box-" + n : "search-box",
      defaultValue: input.value,
      name: input.name,
      placeholder: input.placeholder,
      minLength: 2,
      source: source(),
      showNoOptionsFound: false,
      displayMenu: "overlay",
      templates: {
        inputValue: function (item) { return item && typeof item !== "string" ? item.name : item || ""; },
        suggestion: suggestion,
      },
      onConfirm: function (item) {
        if (item && item.url) window.location.assign(item.url);
      },
    });

    // the library keeps enter for choosing a suggestion; with focus still in the box none is
    // chosen, so enter runs the full search as the plain form does
    const box = container.querySelector("input");
    box.setAttribute("aria-label", "Search bands, artists, venues and shows");
    box.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && box.value.trim()) {
        event.stopPropagation();
        form.submit();
      }
    }, true);
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (typeof accessibleAutocomplete !== "function") return;
    document.querySelectorAll("input[type=search][data-suggest]").forEach(mount);
  });
})();
