// the narrow-screen menu button (see base.html): it only flips aria-expanded, and the styles
// in header.scss show or hide the links from that. a real button, so Enter and Space work.
(function () {
  const button = document.querySelector(".menu-button");
  if (!button) {
    return;
  }
  button.addEventListener("click", function () {
    button.setAttribute("aria-expanded", button.getAttribute("aria-expanded") === "true" ? "false" : "true");
  });
})();
