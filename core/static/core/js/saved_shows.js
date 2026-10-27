// saving shows (see core/saved_shows.py): each event's SAVE link toggles its id in the
// visitor's saved_shows cookie, newest first, and the header's "Saved shows" link counts
// them. the event html is the same for everyone, so the links are shown and labelled here,
// from the cookie. listening on document covers the map panel's copies of events.
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
  // again, for ever
  function setText(element, text) {
    if (element.textContent !== text) {
      element.textContent = text;
    }
  }

  function render(ids) {
    const saved = new Set(ids);
    document.querySelectorAll("a.save[data-event-id]").forEach(function (link) {
      const isSaved = saved.has(link.dataset.eventId);
      setText(link, isSaved ? "SAVED" : "SAVE");
      link.setAttribute("aria-pressed", isSaved ? "true" : "false");
      link.classList.toggle("is-saved", isSaved);
      const wrap = link.closest(".save-wrap");
      if (wrap) {
        wrap.hidden = false;
      }
    });
    document.querySelectorAll("a.saved-count").forEach(function (link) {
      setText(link, ids.length ? "Saved shows (" + ids.length + ")" : "Saved shows");
    });
  }

  document.addEventListener("click", function (e) {
    const link = e.target.closest && e.target.closest("a.save[data-event-id]");
    if (!link) {
      return;
    }
    e.preventDefault();
    const id = link.dataset.eventId;
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
