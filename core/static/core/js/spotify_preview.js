// the listing's spotify play buttons (see core/templates/core/event.html): each is a link
// to the artist on spotify, which with javascript opens spotify's embedded artist player
// below the event's buttons instead. nothing loads from spotify until a click, and only one
// player is open at a time. listening on document covers the map panel's copies of events.
document.addEventListener("click", function (e) {
  const button = e.target.closest && e.target.closest("a.spotify-play[data-spotify-artist]");
  if (!button) {
    return;
  }
  e.preventDefault();

  const row = button.closest(".spotify-artists");
  const open = document.querySelector(".spotify-player");
  const wasThisOne = open && open.dataset.spotifyArtist === button.dataset.spotifyArtist
    && open.previousElementSibling === row;
  if (open) {
    open.remove();
  }
  if (wasThisOne) {
    return;
  }

  const player = document.createElement("iframe");
  player.className = "spotify-player";
  player.dataset.spotifyArtist = button.dataset.spotifyArtist;
  player.src = "https://open.spotify.com/embed/artist/" + encodeURIComponent(button.dataset.spotifyArtist);
  // as spotify's "creating an embed" guide gives it; 152 is the compact height
  player.width = "100%";
  player.height = "152";
  player.frameBorder = "0";
  player.allowFullscreen = true;
  player.loading = "lazy";
  player.allow = "autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture";
  player.title = button.title;
  row.after(player);
});
