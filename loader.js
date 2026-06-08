(function () {
  const loader = document.getElementById("page-loader");
  if (!loader) return;

  document.body.classList.add("page-loading");

  const MIN_MS = 2500;
  const start = Date.now();

  function hideLoader() {
    const elapsed = Date.now() - start;
    const remaining = Math.max(0, MIN_MS - elapsed);

    setTimeout(function () {
      loader.classList.add("is-hidden");
      document.body.classList.remove("page-loading");
      loader.setAttribute("aria-hidden", "true");

      setTimeout(function () {
        loader.remove();
      }, 650);
    }, remaining);
  }

  if (document.readyState === "complete") {
    hideLoader();
  } else {
    window.addEventListener("load", hideLoader);
  }
})();
