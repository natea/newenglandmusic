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

// youtube's own player, unchanged and with nothing over it, as its required minimum
// functionality asks (the css keeps it at least 200px each way), from youtube-nocookie.com,
// which sets no cookies until the visitor plays. a matched video plays; a channel matched by
// id alone plays its uploads, whose playlist is the channel's id with "UC" made "UU". no
// autoplay: the visitor presses play in youtube's player. the referrer policy is the one
// youtube asks for, so its player knows which site embeds it
function youtubePlayer(button) {
  const box = document.createElement("div");
  box.className = "youtube-player";

  const player = document.createElement("iframe");
  const video = button.dataset.youtubeVideo;
  player.src = video
    ? "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(video)
    : "https://www.youtube-nocookie.com/embed/videoseries?list=UU" + encodeURIComponent(button.dataset.youtubeChannel.slice(2));
  player.frameBorder = "0";
  player.allowFullscreen = true;
  player.allow = "encrypted-media; picture-in-picture; fullscreen";
  player.referrerPolicy = "strict-origin-when-cross-origin";
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
