// saving shows in place (see core/saved_shows.py): each event's bookmark toggles its id in
// the visitor's saved_shows cookie, newest first, and the header's "Saved shows" link counts
// them. the page already shows each bookmark's state (core/event_actions.py), and without
// javascript the bookmark's form saves through the server; this saves without a reload, and
// keeps every copy of an event in step. listening on document covers the map panel's copies.
(function () {
  const COOKIE = "saved_shows";
  const MAX_SAVED = 300;
  const MAX_AGE = 365 * 24 * 60 * 60;

  function readSaved() {
    const match = document.cookie.match(new RegExp("(?:^|; )" + COOKIE + "=([^;]*)"));
    const seen = new Set();
    return (match ? decodeURIComponent(match[1]) : "").split(",")
      .map(function (part) { return part.trim(); })
      .filter(function (part) {
        if (!/^\d+$/.test(part) || Number(part) <= 0 || seen.has(part)) {
          return false;
        }
        seen.add(part);
        return true;
      })
      .slice(0, MAX_SAVED);
  }

  function writeSaved(ids) {
    document.cookie = COOKIE + "=" + encodeURIComponent(ids.join(","))
      + "; max-age=" + MAX_AGE + "; path=/; SameSite=Lax";
  }

  // only what differs is changed: rewriting the same text would wake the observer below
  // again, for ever (the header count's text)
  function setText(element, text) {
    if (element.textContent !== text) {
      element.textContent = text;
    }
  }

  function render(ids) {
    const saved = new Set(ids);
    document.querySelectorAll(".save[data-event-id]").forEach(function (button) {
      const isSaved = saved.has(button.dataset.eventId);
      const label = isSaved ? "Saved (click to remove)" : "Save show";
      // attributes, not text: the observer below only watches for added elements
      // the title is its accessible name too: the button has no text
      if (button.title !== label) {
        button.title = label;
      }
      button.setAttribute("aria-pressed", isSaved ? "true" : "false");
      button.classList.toggle("is-saved", isSaved);
    });
    document.querySelectorAll("a.saved-count").forEach(function (link) {
      setText(link, ids.length ? "Saved shows (" + ids.length + ")" : "Saved shows");
    });
  }

  document.addEventListener("click", function (e) {
    const button = e.target.closest && e.target.closest(".save[data-event-id]");
    if (!button) {
      return;
    }
    // saved here, in place: the form's post is only for browsers without javascript
    e.preventDefault();
    const id = button.dataset.eventId;
    let ids = readSaved();
    if (ids.includes(id)) {
      ids = ids.filter(function (saved) { return saved !== id; });
    } else {
      // newest first; past the limit, the oldest saved goes
      ids = [id].concat(ids).slice(0, MAX_SAVED);
    }
    writeSaved(ids);
    render(ids);
  });

  // copies of events added later (the day map's panel) are labelled when they appear, at
  // most once a frame however many changes come at once
  let scheduled = false;
  new MutationObserver(function () {
    if (scheduled) {
      return;
    }
    scheduled = true;
    requestAnimationFrame(function () {
      scheduled = false;
      render(readSaved());
    });
  }).observe(document.documentElement, { childList: true, subtree: true });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { render(readSaved()); });
  } else {
    render(readSaved());
  }
})();
