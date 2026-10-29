// the venue list's "show Google's name": asks for one review venue's place name on click,
// and puts it in place of the link. nothing is asked of google until then.
document.addEventListener("click", async (event) => {
  const link = event.target.closest("a[data-google-name]");
  if (!link) return;
  event.preventDefault();
  link.textContent = "asking Google…";
  try {
    const response = await fetch(link.href, { cache: "no-store", credentials: "same-origin" });
    link.replaceWith(document.createTextNode(response.ok ? await response.text() : `couldn't ask (HTTP ${response.status})`));
  } catch (error) {
    link.textContent = "couldn't ask Google; try again";
  }
});
