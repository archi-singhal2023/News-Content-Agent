document.addEventListener("DOMContentLoaded", async () => {
  wireScrollArrows();

  const page = document.querySelector(".category-page");
  const category = page.dataset.category;

  try {
    const items = await fetchTopics({ category });
    const half = Math.ceil(items.length / 2);
    renderCarousel(document.getElementById("row-a"), items.slice(0, half));
    renderCarousel(document.getElementById("row-b"), items.slice(half));

    if (items.length === 0) {
      document.getElementById("empty-note").style.display = "block";
    }
  } catch (err) {
    console.error(err);
  }
});