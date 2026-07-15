document.addEventListener("DOMContentLoaded", () => {
  const wrap = document.getElementById("menu-dropdown");
  const btn = document.getElementById("hamburger-btn");
  const panel = document.getElementById("dropdown-panel");
  if (!wrap || !btn || !panel) return;

  const open = () => {
    wrap.classList.add("open");
    btn.setAttribute("aria-expanded", "true");
  };
  const close = () => {
    wrap.classList.remove("open");
    btn.setAttribute("aria-expanded", "false");
  };
  const toggle = () => (wrap.classList.contains("open") ? close() : open());

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    toggle();
  });

  // Hover support for pointer devices, in addition to click/tap.
  wrap.addEventListener("mouseenter", open);
  wrap.addEventListener("mouseleave", close);

  document.addEventListener("click", (e) => {
    if (!wrap.contains(e.target)) close();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
  });
});