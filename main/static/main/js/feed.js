(function () {
  const openBtn = document.getElementById("feed-composer-open");
  const photoTrigger = document.getElementById("feed-photo-trigger");
  const form = document.getElementById("feed-upload-form");
  const fileInput = document.getElementById("feed-photo");
  const previewWrap = document.getElementById("feed-photo-preview");
  const previewImg = document.getElementById("feed-photo-preview-img");

  function expandComposer() {
    if (!form) return;
    form.classList.remove("is-collapsed");
    const caption = document.getElementById("feed-caption");
    if (caption) caption.focus();
  }

  if (openBtn) {
    openBtn.addEventListener("click", expandComposer);
  }

  if (photoTrigger && fileInput) {
    photoTrigger.addEventListener("click", function () {
      expandComposer();
      fileInput.click();
    });
  }

  if (fileInput && previewWrap && previewImg) {
    fileInput.addEventListener("change", function () {
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        previewWrap.classList.remove("has-image");
        previewImg.removeAttribute("src");
        return;
      }
      const reader = new FileReader();
      reader.onload = function (e) {
        previewImg.src = e.target.result;
        previewWrap.classList.add("has-image");
        previewWrap.setAttribute("aria-hidden", "false");
      };
      reader.readAsDataURL(file);
    });
  }

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
        form.classList.add("is-collapsed");
        if (previewWrap) {
          previewWrap.classList.remove("has-image");
          previewImg.removeAttribute("src");
        }
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
    const btn = event.target.closest(".feed-heart-btn");
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
      const post = btn.closest(".feed-post");
      const stats = post && post.querySelector(".feed-post-stats");
      if (stats) stats.innerHTML = "<span>♥ " + result.like_count + "</span>";
      let countInBtn = btn.querySelector(".feed-like-count");
      if (!countInBtn) {
        countInBtn = document.createElement("span");
        countInBtn.className = "feed-like-count";
        btn.appendChild(countInBtn);
      }
      countInBtn.textContent = "(" + result.like_count + ")";
    } catch {
      btn.disabled = false;
      alert("Unable to love this post right now.");
    }
  });
})();
