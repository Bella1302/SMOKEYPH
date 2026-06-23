(function () {
  const form = document.getElementById("feed-upload-form");
  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn) submitBtn.disabled = true;
      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
        });
        const result = await response.json();
        if (!response.ok || !result.ok) {
          throw new Error(result.error || "Upload failed.");
        }
        alert(result.message || "Submitted for approval.");
        form.reset();
      } catch (error) {
        alert(error.message || "Unable to upload right now.");
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  function getCsrfToken() {
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  document.addEventListener("click", async (event) => {
    const btn = event.target.closest(".feed-like-btn");
    if (!btn || btn.disabled || btn.classList.contains("is-liked")) return;
    const postId = btn.getAttribute("data-post-id");
    if (!postId) return;
    btn.disabled = true;
    try {
      const fd = new FormData();
      fd.append("csrfmiddlewaretoken", getCsrfToken());
      const response = await fetch("/feed/" + postId + "/like/", {
        method: "POST",
        body: fd,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error("Like failed");
      btn.classList.add("is-liked");
      const countEl = btn.querySelector(".feed-like-count");
      if (countEl) countEl.textContent = result.like_count;
    } catch {
      btn.disabled = false;
      alert("Unable to like this post right now.");
    }
  });
})();
