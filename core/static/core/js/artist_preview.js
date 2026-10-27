// the listing's play buttons (see core/templates/core/event.html): each is a link to the
// artist on spotify or apple music, which with javascript opens that service's embedded
// player below the event's buttons instead. nothing loads from either service until a
// click, and only one player is open at a time, across both. listening on document covers
// the map panel's copies of events.
document.addEventListener("click", function (e) {
  const button = e.target.closest && e.target.closest("a.spotify-play[data-spotify-artist], a.apple-play[data-apple-song]");
  if (!button) {
    return;
  }
  e.preventDefault();

  const row = button.closest(".artist-previews");
  const id = button.classList.contains("apple-play") ? "apple:" + button.dataset.appleSong : "spotify:" + button.dataset.spotifyArtist;
  const open = document.querySelector(".artist-player");
  const wasThisOne = open && open.dataset.playing === id && open.previousElementSibling === row;
  if (open) {
    open.remove();
  }
  if (wasThisOne) {
    return;
  }

  const player = button.classList.contains("apple-play") ? applePlayer(button) : spotifyPlayer(button);
  player.classList.add("artist-player");
  player.dataset.playing = id;
  row.after(player);
});

// as spotify's "creating an embed" guide gives it; 152 is the compact height
function spotifyPlayer(button) {
  const player = document.createElement("iframe");
  player.className = "spotify-player";
  player.src = "https://open.spotify.com/embed/artist/" + encodeURIComponent(button.dataset.spotifyArtist);
  player.width = "100%";
  player.height = "152";
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
function applePlayer(button) {
  const box = document.createElement("div");
  box.className = "apple-player";

  const player = document.createElement("iframe");
  player.src = "https://embed.music.apple.com/us/album/" + encodeURIComponent(button.dataset.appleAlbum)
    + "?i=" + encodeURIComponent(button.dataset.appleSong);
  player.width = "100%";
  player.height = "175";
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
