document.addEventListener("DOMContentLoaded", async () => {
  wireScrollArrows();

  try {
    const [trending, india, intl] = await Promise.all([
      fetchTopics({ tag: "trending" }),
      fetchTopics({ tag: "india" }),
      fetchTopics({ tag: "international" }),
    ]);
    renderCarousel(document.getElementById("trending-track"), trending);
    renderCarousel(document.getElementById("india-track"), india);
    renderCarousel(document.getElementById("intl-track"), intl);
  } catch (err) {
    console.error(err);
  }

  const form = document.getElementById("search-form");
  const input = document.getElementById("search-input");
  const submitBtn = document.getElementById("search-submit");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;

    submitBtn.disabled = true;
    const originalLabel = submitBtn.textContent;
    submitBtn.textContent = "…";

    try {
      const result = await postExplain(query);
      window.location.href = `/topic/${encodeURIComponent(result.id)}`;
    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.textContent = originalLabel;
      alert("Something went wrong finding that story. Please try again.");
    }
  });

  window.addEventListener("pageshow", (event) => {
  if (event.persisted) {
    // Page was restored from bfcache (e.g. browser Back button) —
    // reset the search form to a clean, usable state.
    const submitBtn = document.getElementById("search-submit");
    const input = document.getElementById("search-input");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Explain";
    }
    if (input) {
      input.value = "";
    }
  }
});
  
});