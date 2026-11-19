// the ☰ button folds the site menu on a phone; without this script the links stay shown
// (the `js` class that hides them is set by the inline snippet in base.html)
document.addEventListener("DOMContentLoaded", function () {
  const button = document.querySelector(".menu-toggle");
  const menu = document.getElementById("siteMenu");
  if (!button || !menu) return;

  button.addEventListener("click", function () {
    const open = button.getAttribute("aria-expanded") !== "true";
    button.setAttribute("aria-expanded", open ? "true" : "false");
    menu.classList.toggle("open", open);
  });
});
