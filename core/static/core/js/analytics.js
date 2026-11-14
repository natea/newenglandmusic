// the site's named events for posthog (add-posthog-analytics): one place that sends them, so
// every script names its events the same way. capture() does nothing unless base.html loaded
// posthog (POSTHOG_PROJECT_TOKEN set), and posthog itself drops events from a browser that
// opted out on the privacy page. never send anything that identifies a person: no names,
// emails, locations or distances, and no form field but the search words.
//
// links the server renders (a show's "tix", its calendar icons, the calendar feed links) are
// caught here, by one listener, so the stored event html needn't change. a link that leaves
// the page is sent with the beacon, at once, so it isn't lost to the navigation.

(function () {
  const LEAVING = { transport: "sendBeacon", send_instantly: true };

  function capture(name, properties, leaving) {
    const posthog = window.posthog;
    if (!posthog || typeof posthog.capture !== "function") return;
    posthog.capture(name, properties || {}, leaving ? LEAVING : undefined);
  }

  window.siteAnalytics = { capture: capture };

  // the show a link belongs to: its row's id is "event-<id>" on every listing
  function showId(element) {
    const row = element.closest("[id^='event-']");
    return row ? row.id.slice("event-".length) : undefined;
  }

  document.addEventListener("click", function (e) {
    const link = e.target.closest && e.target.closest("a.ticket, a.ical, a.gcal, a.calendarLink");
    if (!link) return;
    if (link.classList.contains("ticket")) {
      capture("ticket_link_opened", { event_id: showId(link) }, true);
    } else if (link.classList.contains("calendarLink")) {
      capture("calendar_feed_subscribed", { how: link.classList.contains("google") ? "google" : "webcal" }, true);
    } else {
      capture("show_added_to_calendar", { how: link.classList.contains("gcal") ? "google" : "ics", event_id: showId(link) }, true);
    }
  });

  // the privacy page's control: posthog's own opt-out, which it remembers in this browser
  function showControl() {
    const posthog = window.posthog;
    const control = document.querySelector(".analytics-control");
    const button = document.getElementById("analytics-toggle");
    if (!posthog || !control || !button || typeof posthog.has_opted_out_capturing !== "function") return;
    const state = document.getElementById("analytics-state");
    function label() {
      const off = posthog.has_opted_out_capturing();
      button.textContent = off ? "Turn analytics back on in this browser" : "Turn off analytics in this browser";
      if (state) state.textContent = off ? "Analytics are off in this browser." : "";
    }
    button.addEventListener("click", function () {
      if (posthog.has_opted_out_capturing()) {
        posthog.opt_in_capturing();
      } else {
        posthog.opt_out_capturing();
      }
      label();
    });
    label();
    control.hidden = false;
  }
  // posthog's loaded callback (base.html) says when its real methods are there
  document.addEventListener("posthog:loaded", showControl);
  if (window.posthog && window.posthog.__loaded) showControl();

  // a full search from the box's form (its button, or the plain form without suggestions);
  // the suggestions' own enter path sends it in search-suggest.js, since form.submit() fires
  // no submit event
  document.addEventListener("submit", function (e) {
    const form = e.target;
    if (!form.matches || !form.matches("form[role=search]")) return;
    const box = form.querySelector("input[name=s]");
    if (box && box.value.trim()) capture("search", { query: box.value.trim() }, true);
  });
})();
