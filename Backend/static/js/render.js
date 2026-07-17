/**
 * render.js — DOM-building helpers shared across pages.
 */

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}

function createCard(item) {
  const card = document.createElement("a");
  card.className = "context-card";
  card.href = `/topic/${encodeURIComponent(item.id)}`;
  card.innerHTML = `
    <div class="card-text">
      <span class="card-eyebrow">${escapeHtml((item.category || "").toUpperCase())}</span>
      <h3 class="card-headline">${escapeHtml(item.headline)}</h3>
    </div>
  `;
  return card;
}

function renderCarousel(trackEl, items) {
  if (!trackEl) return;
  trackEl.innerHTML = "";
  items.forEach((item) => trackEl.appendChild(createCard(item)));
}

function wireScrollArrows(root = document) {
  root.querySelectorAll(".scroll-arrow").forEach((btn) => {
    btn.addEventListener("click", () => {
      const track = document.getElementById(btn.dataset.target);
      if (!track) return;
      const dir = btn.classList.contains("left") ? -1 : 1;
      track.scrollBy({ left: dir * 300, behavior: "smooth" });
    });
  });
}

function sourcesHtml(sources) {
  return (sources || [])
    .map(
      (s) =>
        `<a href="${escapeHtml(s.url)}" target="_blank" rel="noreferrer" class="source-link">${escapeHtml(s.title)} ↗</a>`
    )
    .join("");
}