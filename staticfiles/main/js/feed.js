(function () {
  const addYoursBtn = document.getElementById("feed-add-yours-btn");
  const modal = document.getElementById("feed-modal");
  const form = document.getElementById("feed-upload-form");
  const fileInput = document.getElementById("feed-photo");
  const previewWrap = document.getElementById("feed-photo-preview");
  const previewImg = document.getElementById("feed-photo-preview-img");
  const statusBanner = document.getElementById("feed-status-banner");
  const modalStatus = document.getElementById("feed-modal-status");

  function showStatus(message, type, inModal) {
    const target = inModal ? modalStatus : statusBanner;
    if (!target) {
      alert(message);
      return;
    }
    target.textContent = message;
    target.hidden = false;
    target.classList.remove("is-error", "is-success");
    if (type) target.classList.add(type);
  }

  function clearModalStatus() {
    if (!modalStatus) return;
    modalStatus.hidden = true;
    modalStatus.textContent = "";
    modalStatus.classList.remove("is-error", "is-success");
  }

  function getCsrfToken() {
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    if (input && input.value) return input.value;
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function openModal() {
    if (!modal) return;
    modal.hidden = false;
    document.body.style.overflow = "hidden";
    clearModalStatus();
    const caption = document.getElementById("feed-caption");
    if (caption) window.setTimeout(function () { caption.focus(); }, 50);
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    document.body.style.overflow = "";
    clearModalStatus();
  }

  if (addYoursBtn) {
    addYoursBtn.addEventListener("click", openModal);
  }

  document.querySelectorAll("[data-feed-modal-close]").forEach(function (el) {
    el.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && modal && !modal.hidden) {
      closeModal();
    }
  });

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
      if (!fileInput || !fileInput.files || !fileInput.files.length) {
        const caption = document.getElementById("feed-caption");
        const hasCaption = caption && caption.value.trim().length > 0;
        if (!hasCaption) {
          showStatus("Write a message or add a photo before posting.", "is-error", true);
          return;
        }
      }

      const submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn) submitBtn.disabled = true;
      clearModalStatus();

      try {
        const fd = new FormData(form);
        const csrf = getCsrfToken();
        if (csrf) fd.set("csrfmiddlewaretoken", csrf);

        const response = await fetch(form.action, {
          method: "POST",
          body: fd,
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrf,
          },
          credentials: "same-origin",
        });

        let result = {};
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          result = await response.json();
        } else {
          throw new Error(
            response.status === 403
              ? "Session expired. Refresh the page and try again."
              : "Upload failed. Please try again."
          );
        }

        if (!response.ok || !result.ok) {
          throw new Error(result.error || "Upload failed.");
        }

        closeModal();
        showStatus(result.message || "Post submitted for approval.", "is-success", false);
        window.setTimeout(function () {
          window.location.reload();
        }, 900);
      } catch (error) {
        showStatus(error.message || "Unable to upload right now.", "is-error", true);
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  document.addEventListener("click", async (event) => {
    const btn = event.target.closest(".feed-heart-btn");
    if (!btn || btn.disabled || btn.classList.contains("is-liked")) return;
    const postId = btn.getAttribute("data-post-id");
    if (!postId) return;
    btn.disabled = true;
    try {
      const csrf = getCsrfToken();
      const fd = new FormData();
      fd.append("csrfmiddlewaretoken", csrf);
      const response = await fetch("/feed/" + postId + "/like/", {
        method: "POST",
        body: fd,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrf,
        },
        credentials: "same-origin",
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
      showStatus("Unable to love this post right now.", "is-error", false);
    }
  });
})();
