// the band discovery deck (core/templates/core/discover.html): turns the page's list of cards
// into a deck of one card at a time. left (swipe, "Skip" button, left arrow) passes an act and
// stores nothing. right (swipe, "Add" button, right arrow) opens a picker of the act's shows;
// its Save applies the ticks to the saved_shows cookie in one write (core/js/saved_shows.js).
// the top card alone has a player (core/js/artist_preview.js): YouTube, else Apple Music, else
// Spotify. the first card waits for a Start press, laid over our own placeholder (its video's
// thumbnail, or a plain dark box) and gone when the player loads; from then on each top card's
// player is loaded in the handler of the swipe, button or key that brought it up, asking
// YouTube to start playing (Apple Music and Spotify load ready). nothing is stored about what
// was passed.
(function () {
  const section = document.querySelector(".discover");
  const deck = section && section.querySelector(".deck");
  if (!deck) {
    return;
  }
  const cards = Array.from(deck.querySelectorAll(".discover-card"));
  const SWIPE_DISTANCE = 80;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let index = 0;
  let picker = null;
  // false until the visitor presses Start: no player loads, and the deck's controls wait
  let started = false;

  section.classList.add("is-deck", "is-waiting");

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text) {
      node.textContent = text;
    }
    return node;
  }

  // the deck's own parts: a stage for the cards, the hint, the buttons, the announcement
  const stage = element("div", "deck-stage");
  deck.before(stage);
  stage.appendChild(deck);
  const hint = element("p", "deck-hint");
  hint.append(element("span", "hint-skip", "← Skip"), element("span", "hint-add", "Add →"));
  const controls = element("div", "deck-controls");
  const skipButton = element("button", "deck-skip", "✕ Skip");
  skipButton.type = "button";
  skipButton.setAttribute("aria-label", "Skip this act");
  const addButton = element("button", "deck-add", "♥ Add");
  addButton.type = "button";
  addButton.setAttribute("aria-label", "Add this act's shows");
  controls.append(skipButton, addButton);
  const keys = element("p", "deck-keys", "Swipe or use the keys: ← skip, → add. The show list opens after Add only.");
  const live = element("div", "deck-live");
  live.setAttribute("role", "status");
  live.setAttribute("aria-live", "polite");
  const end = element("div", "deck-end");
  end.hidden = true;
  end.setAttribute("tabindex", "-1");
  end.append(element("p", "deck-end-text", "That's every band in the deck."));
  const again = element("button", "deck-again", "Start again");
  again.type = "button";
  const saved = element("a", "deck-saved", "Open saved shows");
  saved.href = "/saved";
  end.append(again, saved);
  stage.after(hint, controls, keys, end, live);

  let hinting = true;
  function stopHint() {
    if (hinting) {
      hinting = false;
      section.classList.remove("is-hinting");
    }
  }

  function top() {
    return cards[index];
  }

  function finished() {
    return index >= cards.length;
  }

  // the player of the top card, and no other: the card's best match, asking to start playing
  // (only youtube's takes it). only called after the visitor's Start or another action
  function loadPlayer(card) {
    const button = card.querySelector("a.youtube-play") || card.querySelector("a.apple-play")
      || card.querySelector("a.spotify-play");
    if (button) {
      window.ArtistPreview.showInCard(card, button, true);
    }
  }

  // the first card's Start control, over our own placeholder in the player's box: the video's
  // thumbnail when the card has a youtube video (this card's only), else a plain dark box. the
  // player is never overlaid: Start removes both before the player loads
  function showStart(card) {
    const box = card.querySelector(".discover-player-box");
    const video = card.querySelector("a.youtube-play");
    const placeholder = element("div", "discover-start");
    if (video && video.dataset.youtubeVideo) {
      const thumbnail = element("img", "discover-thumbnail");
      thumbnail.src = "https://i.ytimg.com/vi/" + encodeURIComponent(video.dataset.youtubeVideo) + "/hqdefault.jpg";
      thumbnail.alt = "";
      placeholder.appendChild(thumbnail);
    }
    const start = element("button", "deck-start", "▶ Start");
    start.type = "button";
    start.addEventListener("click", startDeck);
    placeholder.append(start, element("span", "discover-start-note", "Music plays on its own once you start"));
    box.replaceChildren(placeholder);
  }

  function startDeck() {
    if (started) {
      return;
    }
    started = true;
    section.classList.remove("is-waiting");
    if (hinting) {
      section.classList.add("is-hinting");
    }
    // the press is the visitor's action: the placeholder and control go as the player loads
    top().querySelector(".discover-player-box").replaceChildren();
    loadPlayer(top());
    addButton.focus();
  }

  function show() {
    cards.forEach(function (card, position) {
      card.hidden = position !== index;
      card.style.transition = "";
      card.style.transform = "";
      if (position !== index) {
        window.ArtistPreview.clearCard(card);
      }
    });
    const done = finished();
    end.hidden = !done;
    controls.hidden = done;
    keys.hidden = done;
    deck.hidden = done;
    if (done) {
      stopHint();
      hint.hidden = true;
      live.textContent = "That's every band in the deck.";
      end.focus();
      return;
    }
    hint.hidden = false;
    if (started) {
      loadPlayer(top());
    } else {
      showStart(top());
    }
    live.textContent = top().dataset.act + ", " + (index + 1) + " of " + cards.length;
  }

  function advance() {
    window.ArtistPreview.clearCard(top());
    index += 1;
    show();
  }

  function moveOff(direction, then) {
    const card = top();
    if (reduceMotion.matches) {
      then();
      return;
    }
    card.style.transition = "transform 160ms ease-out";
    card.style.transform = "translateX(" + direction * 120 + "%)";
    setTimeout(then, 170);
  }

  function skip() {
    stopHint();
    moveOff(-1, advance);
  }

  function add() {
    stopHint();
    openPicker();
  }

  // the picker: the act's shows soonest first, ticked if already saved. nothing changes until
  // Save, and Save with the ticks as they were saved changes nothing
  function openPicker() {
    if (picker || finished()) {
      return;
    }
    const card = top();
    const savedIds = new Set(window.SavedShows.ids());
    const dialog = element("div", "picker");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    const title = element("h3", "picker-title", card.dataset.act + ": choose shows");
    title.id = "picker-title";
    dialog.setAttribute("aria-labelledby", title.id);
    const list = element("ul", "picker-shows");
    card.querySelectorAll(".discover-shows li").forEach(function (item) {
      const id = item.dataset.eventId;
      const row = element("li");
      const label = element("label", "picker-row");
      const box = element("input");
      box.type = "checkbox";
      box.value = id;
      box.checked = savedIds.has(id);
      box.dataset.wasSaved = box.checked ? "1" : "";
      const text = element("span", "picker-text");
      text.append(
        element("strong", "", item.querySelector(".show-date").textContent),
        " · " + item.querySelector(".show-time").textContent + " · " + item.querySelector(".show-where").textContent,
      );
      label.append(box, text);
      if (box.checked) {
        label.append(element("span", "picker-saved", "Saved"));
      }
      row.appendChild(label);
      list.appendChild(row);
    });
    const save = element("button", "picker-save");
    save.type = "button";
    const close = element("button", "picker-close", "Cancel");
    close.type = "button";
    const boxes = Array.from(list.querySelectorAll("input"));
    function ticked() {
      return boxes.filter(function (box) { return box.checked; });
    }
    function label() {
      const count = ticked().length;
      save.textContent = "Save " + count + " show" + (count === 1 ? "" : "s");
    }
    label();
    boxes.forEach(function (box) { box.addEventListener("change", label); });
    save.addEventListener("click", function () {
      const additions = boxes.filter(function (box) { return box.checked && !box.dataset.wasSaved; });
      const removals = boxes.filter(function (box) { return !box.checked && box.dataset.wasSaved; });
      if (!additions.length && !removals.length) {
        return;
      }
      window.SavedShows.apply(
        additions.map(function (box) { return box.value; }),
        removals.map(function (box) { return box.value; }),
      );
      closePicker(false);
      advance();
    });
    close.addEventListener("click", function () { closePicker(true); });
    const actions = element("div", "picker-actions");
    actions.append(save, close);
    dialog.append(title, element("p", "picker-note", "Tap a row to tick it. Nothing is saved until you press Save."), list, actions);
    dialog.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        e.preventDefault();
        closePicker(true);
      }
    });
    section.appendChild(dialog);
    picker = { dialog: dialog, opener: document.activeElement };
    // the deck behind it can't be reached while it's open
    [stage, hint, controls, keys].forEach(function (part) { part.inert = true; });
    (boxes[0] || save).focus();
  }

  function closePicker(restoreFocus) {
    if (!picker) {
      return;
    }
    const opener = picker.opener;
    picker.dialog.remove();
    picker = null;
    [stage, hint, controls, keys].forEach(function (part) { part.inert = false; });
    if (restoreFocus) {
      (opener && document.contains(opener) ? opener : addButton).focus();
    }
  }

  skipButton.addEventListener("click", skip);
  addButton.addEventListener("click", add);
  again.addEventListener("click", function () {
    index = 0;
    show();
    addButton.focus();
  });

  document.addEventListener("keydown", function (e) {
    if (!started || picker || finished() || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) {
      return;
    }
    const target = e.target;
    if (target.closest && target.closest("input, textarea, select, [contenteditable]")) {
      return;
    }
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      skip();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      add();
    }
  });

  // swiping: a drag that starts on the card outside its player box. the player takes its own
  // pointer events (an iframe's never reach this page), and a start inside its box is ignored
  let drag = null;
  let dragged = false;
  stage.addEventListener("pointerdown", function (e) {
    const card = top();
    if (!started || !card || !card.contains(e.target) || e.target.closest(".discover-player-box") || (e.pointerType === "mouse" && e.button !== 0)) {
      return;
    }
    drag = { id: e.pointerId, x: e.clientX, y: e.clientY, moved: 0 };
    dragged = false;
  });
  // a link or photo dragged would start the browser's own drag and cancel the swipe
  stage.addEventListener("dragstart", function (e) { e.preventDefault(); });
  stage.addEventListener("pointermove", function (e) {
    if (!drag || e.pointerId !== drag.id) {
      return;
    }
    const dx = e.clientX - drag.x;
    if (!dragged && Math.abs(dx) < 6) {
      return;
    }
    if (!dragged) {
      dragged = true;
      stopHint();
      stage.setPointerCapture(e.pointerId);
    }
    drag.moved = dx;
    const card = top();
    card.style.transition = "none";
    card.style.transform = "translateX(" + dx + "px) rotate(" + dx / 40 + "deg)";
  });
  function release(e) {
    if (!drag || e.pointerId !== drag.id) {
      return;
    }
    const moved = drag.moved;
    drag = null;
    if (!dragged) {
      return;
    }
    const card = top();
    if (Math.abs(moved) < SWIPE_DISTANCE) {
      // a short drag snaps back
      card.style.transition = "transform 160ms ease-out";
      card.style.transform = "";
    } else if (moved < 0) {
      skip();
    } else {
      // the card goes back where it was, and the picker opens
      card.style.transition = "transform 160ms ease-out";
      card.style.transform = "";
      add();
    }
  }
  stage.addEventListener("pointerup", release);
  stage.addEventListener("pointercancel", release);
  // a drag that ends on a link (the act's name) is not a click on it
  stage.addEventListener("click", function (e) {
    if (dragged) {
      e.preventDefault();
      e.stopPropagation();
      dragged = false;
    }
  }, true);

  controls.addEventListener("click", stopHint, true);
  show();
})();
