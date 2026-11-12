// the listing's play buttons (see core/templates/core/event.html): each is a link to the
// artist on spotify, apple music or youtube, which with javascript opens that service's
// embedded player below the event's buttons instead. nothing loads from any of them until
// a click, and only one player is open at a time, across all three. listening on document
// covers the map panel's copies of events.
document.addEventListener("click", function (e) {
  const button = e.target.closest
    && e.target.closest("a.spotify-play[data-spotify-artist], a.apple-play[data-apple-song], a.youtube-play[data-youtube-channel]");
  if (!button) {
    return;
  }
  e.preventDefault();

  // the discovery deck's card has a player of its own, which this button replaces
  const card = button.closest(".discover-card");
  if (card) {
    showInCard(card, button);
    return;
  }

  const row = button.closest(".artist-previews");
  const id = playerId(button);
  const open = document.querySelector(".artist-player");
  const wasThisOne = open && open.dataset.playing === id && open.previousElementSibling === row;
  if (open) {
    open.remove();
  }
  if (wasThisOne) {
    return;
  }

  const player = button.classList.contains("apple-play") ? applePlayer(button)
    : button.classList.contains("youtube-play") ? youtubePlayer(button) : spotifyPlayer(button);
  player.classList.add("artist-player");
  player.dataset.playing = id;
  row.after(player);
});

function playerId(button) {
  if (button.classList.contains("apple-play")) {
    return "apple:" + button.dataset.appleSong;
  }
  if (button.classList.contains("youtube-play")) {
    return "youtube:" + (button.dataset.youtubeVideo || button.dataset.youtubeChannel);
  }
  return "spotify:" + button.dataset.spotifyArtist;
}

// the discovery deck's card (core/js/discover.js) hosts one player in its .discover-player-box,
// the card's own: pressing one of the card's play buttons replaces it with that service's
// (pressing the one shown leaves it), and the listings' one-player rule isn't involved. the
// height is at least 200px, which youtube's rules ask of its player and the others share
const CARD_PLAYER_HEIGHT = 232;

function playerFor(button, height, autoplay) {
  return button.classList.contains("apple-play") ? applePlayer(button, height)
    : button.classList.contains("youtube-play") ? youtubePlayer(button, height, autoplay) : spotifyPlayer(button, height);
}

// autoplay asks the service to start playing, which only youtube's embed takes by a documented
// parameter: apple music's and spotify's load ready, with their own play control. the deck
// asks only after the visitor's own action (its Start, a swipe, a button or a key)
function showInCard(card, button, autoplay) {
  const box = card.querySelector(".discover-player-box");
  const id = playerId(button);
  if (!box || box.dataset.playing === id) {
    return;
  }
  const player = playerFor(button, CARD_PLAYER_HEIGHT, autoplay);
  // the card is on top: its player is wanted now, not when scrolled to
  player.querySelectorAll("iframe").forEach(function (frame) { frame.loading = "eager"; });
  if (player.tagName === "IFRAME") {
    player.loading = "eager";
  }
  player.classList.add("discover-player");
  box.replaceChildren(player);
  box.dataset.playing = id;
}

function clearCard(card) {
  const box = card.querySelector(".discover-player-box");
  if (box) {
    box.replaceChildren();
    delete box.dataset.playing;
  }
}

// the youtube iframe of a deck card, for the deck to post commands to and hear messages from
function youtubeFrame(card) {
  return card.querySelector(".discover-player-box .youtube-player iframe");
}

window.ArtistPreview = { spotifyPlayer, applePlayer, youtubePlayer, showInCard, clearCard, youtubeFrame };

// as spotify's "creating an embed" guide gives it; 152 is the compact height
function spotifyPlayer(button, height) {
  const player = document.createElement("iframe");
  player.className = "spotify-player";
  player.src = "https://open.spotify.com/embed/artist/" + encodeURIComponent(button.dataset.spotifyArtist);
  player.width = "100%";
  player.height = String(height || 152);
  player.frameBorder = "0";
  player.allowFullscreen = true;
  player.loading = "lazy";
  player.allow = "autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture";
  player.title = button.title;
  return player;
}

// the artist's top song in apple's player, which plays a preview for everyone (apple's
// artist player plays nothing for visitors not signed in), then a link to the artist's page.
// the attributes are those of apple's own embed code
function applePlayer(button, height) {
  const box = document.createElement("div");
  box.className = "apple-player";

  const player = document.createElement("iframe");
  player.src = "https://embed.music.apple.com/us/album/" + encodeURIComponent(button.dataset.appleAlbum)
    + "?i=" + encodeURIComponent(button.dataset.appleSong);
  player.width = "100%";
  player.height = String(height || 175);
  player.frameBorder = "0";
  player.loading = "lazy";
  player.allow = "autoplay *; encrypted-media *; fullscreen *; clipboard-write";
  player.setAttribute("sandbox", "allow-forms allow-popups allow-same-origin allow-scripts "
    + "allow-storage-access-by-user-activation allow-top-navigation-by-user-activation");
  player.title = button.title;
  box.appendChild(player);

  const more = document.createElement("a");
  more.className = "apple-more";
  more.href = button.href;
  more.target = "_blank";
  more.rel = "noopener";
  more.textContent = "More by " + button.dataset.artistName + " on Apple Music";
  box.appendChild(more);
  return box;
}

// youtube's own player, unchanged and with nothing over it, as its required minimum
// functionality asks (the css keeps it at least 200px each way), from youtube-nocookie.com,
// which sets no cookies until the visitor plays. a matched video plays; a channel matched by
// id alone plays its uploads, whose playlist is the channel's id with "UC" made "UU". no
// autoplay in the listings: the visitor presses play in youtube's player. the discovery deck
// passes autoplay after the visitor's action, and gets autoplay=1 (and playsinline=1 for ios),
// an allow that includes autoplay, and enablejsapi=1 with the page's origin, so the deck can
// post youtube's player commands to it and hear its messages (core/js/discover.js). the
// listings' player has none of them. the referrer policy is the one
// youtube asks for, so its player knows which site embeds it
function youtubePlayer(button, height, autoplay) {
  const box = document.createElement("div");
  box.className = "youtube-player";

  const player = document.createElement("iframe");
  const video = button.dataset.youtubeVideo;
  player.src = video
    ? "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(video)
    : "https://www.youtube-nocookie.com/embed/videoseries?list=UU" + encodeURIComponent(button.dataset.youtubeChannel.slice(2));
  player.frameBorder = "0";
  player.allowFullscreen = true;
  player.allow = autoplay ? "autoplay; encrypted-media; picture-in-picture; fullscreen" : "encrypted-media; picture-in-picture; fullscreen";
  if (autoplay) {
    player.src += (player.src.includes("?") ? "&" : "?") + "autoplay=1&playsinline=1&enablejsapi=1&origin="
      + encodeURIComponent(window.location.origin);
  }
  player.referrerPolicy = "strict-origin-when-cross-origin";
  if (height) {
    player.height = String(height);
  }
  player.title = button.title;
  box.appendChild(player);

  const more = document.createElement("a");
  more.className = "youtube-more";
  more.href = button.dataset.youtubeChannel
    ? "https://www.youtube.com/channel/" + encodeURIComponent(button.dataset.youtubeChannel)
    : button.href;
  more.target = "_blank";
  more.rel = "noopener";
  more.textContent = "More by " + button.dataset.artistName + " on YouTube";
  box.appendChild(more);
  return box;
}
