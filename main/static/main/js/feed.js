(function () {
  const addYoursBtn = document.getElementById("feed-add-yours-btn");
  const addAlbumBtn = document.getElementById("feed-add-album-btn");
  const modal = document.getElementById("feed-modal");
  const albumModal = document.getElementById("feed-album-modal");
  const form = document.getElementById("feed-upload-form");
  const albumForm = document.getElementById("feed-album-form");
  const fileInput = document.getElementById("feed-photo");
  const albumPhotosInput = document.getElementById("feed-album-photos-input");
  const previewWrap = document.getElementById("feed-photo-preview");
  const previewImg = document.getElementById("feed-photo-preview-img");
  const albumPreview = document.getElementById("feed-album-preview");
  const statusBanner = document.getElementById("feed-status-banner");
  const modalStatus = document.getElementById("feed-modal-status");
  const albumModalStatus = document.getElementById("feed-album-modal-status");

  function showStatus(message, type, target) {
    if (!target) {
      alert(message);
      return;
    }
    target.textContent = message;
    target.hidden = false;
    target.classList.remove("is-error", "is-success");
    if (type) target.classList.add(type);
  }

  function clearStatus(target) {
    if (!target) return;
    target.hidden = true;
    target.textContent = "";
    target.classList.remove("is-error", "is-success");
  }

  function getCsrfToken() {
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    if (input && input.value) return input.value;
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function openModal(which) {
    const el = which === "album" ? albumModal : modal;
    if (!el) return;
    el.hidden = false;
    document.body.style.overflow = "hidden";
    clearStatus(which === "album" ? albumModalStatus : modalStatus);
  }

  function closeModal(which) {
    const el = which === "album" ? albumModal : modal;
    if (!el) return;
    el.hidden = true;
    document.body.style.overflow = "";
    clearStatus(which === "album" ? albumModalStatus : modalStatus);
  }

  if (addYoursBtn) {
    addYoursBtn.addEventListener("click", function () {
      openModal("post");
      const caption = document.getElementById("feed-caption");
      if (caption) window.setTimeout(function () { caption.focus(); }, 50);
    });
  }

  if (addAlbumBtn) {
    addAlbumBtn.addEventListener("click", function () {
      openModal("album");
      const title = document.getElementById("feed-album-title-input");
      if (title) window.setTimeout(function () { title.focus(); }, 50);
    });
  }

  document.querySelectorAll("[data-feed-modal-close]").forEach(function (el) {
    el.addEventListener("click", function () { closeModal("post"); });
  });

  document.querySelectorAll("[data-album-modal-close]").forEach(function (el) {
    el.addEventListener("click", function () { closeModal("album"); });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    if (modal && !modal.hidden) closeModal("post");
    if (albumModal && !albumModal.hidden) closeModal("album");
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

  if (albumPhotosInput && albumPreview) {
    albumPhotosInput.addEventListener("change", function () {
      albumPreview.innerHTML = "";
      const files = albumPhotosInput.files;
      if (!files || !files.length) {
        albumPreview.classList.remove("has-images");
        albumPreview.setAttribute("aria-hidden", "true");
        return;
      }
      albumPreview.classList.add("has-images");
      albumPreview.setAttribute("aria-hidden", "false");
      Array.from(files).slice(0, 12).forEach(function (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
          const img = document.createElement("img");
          img.src = e.target.result;
          img.alt = "";
          albumPreview.appendChild(img);
        };
        reader.readAsDataURL(file);
      });
    });
  }

  async function submitForm(event, formEl, statusEl, modalName) {
    event.preventDefault();
    const submitBtn = formEl.querySelector("button[type='submit']");
    if (submitBtn) submitBtn.disabled = true;
    clearStatus(statusEl);

    try {
      const fd = new FormData(formEl);
      const csrf = getCsrfToken();
      if (csrf) fd.set("csrfmiddlewaretoken", csrf);

      const response = await fetch(formEl.action, {
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

      closeModal(modalName);
      showStatus(result.message || "Submitted for approval.", "is-success", statusBanner);
      window.setTimeout(function () {
        window.location.reload();
      }, 900);
    } catch (error) {
      showStatus(error.message || "Unable to upload right now.", "is-error", statusEl);
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  if (form) {
    form.addEventListener("submit", async function (event) {
      if (!fileInput || !fileInput.files || !fileInput.files.length) {
        const caption = document.getElementById("feed-caption");
        const hasCaption = caption && caption.value.trim().length > 0;
        if (!hasCaption) {
          showStatus("Write a message or add a photo before posting.", "is-error", modalStatus);
          event.preventDefault();
          return;
        }
      }
      await submitForm(event, form, modalStatus, "post");
    });
  }

  if (albumForm) {
    albumForm.addEventListener("submit", async function (event) {
      if (!albumPhotosInput || !albumPhotosInput.files || !albumPhotosInput.files.length) {
        showStatus("Add at least one photo to your album.", "is-error", albumModalStatus);
        event.preventDefault();
        return;
      }
      await submitForm(event, albumForm, albumModalStatus, "album");
    });
  }

  document.addEventListener("click", async function (event) {
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
      showStatus("Unable to love this post right now.", "is-error", statusBanner);
    }
  });
})();
