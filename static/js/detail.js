document.addEventListener("DOMContentLoaded", async () => {
  const page = document.querySelector(".detail-page");
  const id = page.dataset.topicId;
  const container = document.getElementById("detail-content");

  try {
    const data = await fetchTopic(id);
    renderDetail(container, data);
  } catch (err) {
    container.innerHTML = `<p class="empty-note">Couldn't find this story.</p>`;
  }
});

function renderDetail(container, data) {
  let sectionsHtml = "";
  if (data.type === "deep_dive" && data.sections && data.sections.length) {
    sectionsHtml =
      `<div class="accordion-list">` +
      data.sections
        .map(
          (sec, i) => `
        <div class="accordion-row" data-index="${i}">
          <button class="accordion-head">
            <span class="accordion-angle">${escapeHtml(sec.angle)}</span>
            <span class="accordion-chevron">⌄</span>
          </button>
          <div class="accordion-body">
            <p class="accordion-paragraph">${escapeHtml(sec.paragraph)}</p>
            <div class="source-row">${sourcesHtml(sec.sources)}</div>
          </div>
        </div>
      `
        )
        .join("") +
      `</div>`;
  }

  const droppedHtml =
    data.dropped_angles && data.dropped_angles.length
      ? `<p class="gap-note">Limited verified coverage on: ${escapeHtml(data.dropped_angles.join(", "))}</p>`
      : "";

  container.innerHTML = `
    <span class="detail-eyebrow">${escapeHtml((data.category || "").toUpperCase())} · ${
    data.type === "deep_dive" ? "DEEP DIVE" : "QUICK READ"
  }</span>
    <h1 class="detail-title">${escapeHtml(data.topic)}</h1>
    <div class="summary-card">
      <p class="summary-text">${escapeHtml(data.summary)}</p>
      <div class="source-row">${sourcesHtml(data.summary_sources)}</div>
    </div>
    ${sectionsHtml}
    ${droppedHtml}
  `;

  container.querySelectorAll(".accordion-head").forEach((btn) => {
    btn.addEventListener("click", () => {
      const row = btn.closest(".accordion-row");
      const wasOpen = row.classList.contains("open");
      container.querySelectorAll(".accordion-row.open").forEach((r) => r.classList.remove("open"));
      if (!wasOpen) row.classList.add("open");
      updateAccordionHeights(container);
    });
  });
}

function updateAccordionHeights(container) {
  container.querySelectorAll(".accordion-row").forEach((row) => {
    const body = row.querySelector(".accordion-body");
    if (row.classList.contains("open")) {
      body.style.maxHeight = body.scrollHeight + "px";
      body.style.padding = "0 4px 18px";
    } else {
      body.style.maxHeight = "0px";
      body.style.padding = "0 4px";
    }
  });
}