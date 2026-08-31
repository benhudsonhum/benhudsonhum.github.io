(() => {
  "use strict";

  const storageKey = "portfolio-theme";
  const root = document.documentElement;
  const colourScheme = window.matchMedia("(prefers-color-scheme: light)");
  const savedTheme = () => {
    try {
      const value = window.localStorage.getItem(storageKey);
      return value === "light" || value === "dark" ? value : null;
    } catch (_error) {
      return null;
    }
  };
  const updateThemeMetadata = (theme) => {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = theme === "light" ? "#f4f0e8" : "#0b0f14";
  };
  const updateThemeButton = (theme) => {
    const button = document.querySelector("[data-theme-toggle]");
    if (!button) return;
    const nextTheme = theme === "dark" ? "light" : "dark";
    const label = `Switch to ${nextTheme} theme`;
    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);
    button.dataset.activeTheme = theme;
  };
  const applyTheme = (theme, persist = false) => {
    root.dataset.theme = theme;
    updateThemeMetadata(theme);
    updateThemeButton(theme);
    if (persist) {
      try {
        window.localStorage.setItem(storageKey, theme);
      } catch (_error) {
        // The selected theme still applies when storage is unavailable.
      }
    }
  };
  applyTheme(root.dataset.theme === "light" ? "light" : "dark");
  const themeToggle = document.querySelector("[data-theme-toggle]");
  if (themeToggle) themeToggle.addEventListener("click", () => applyTheme(root.dataset.theme === "dark" ? "light" : "dark", true));
  colourScheme.addEventListener("change", (event) => {
    if (!savedTheme()) applyTheme(event.matches ? "light" : "dark");
  });

  const nestedInteractiveSelector = 'video, audio, button, a, input, select, textarea, [contenteditable], [role="slider"]';
  const flipbookApis = new Map();
  document.querySelectorAll("[data-flipbook]").forEach((flipbook) => {
    const slides = Array.from(flipbook.querySelectorAll(".flipbook__slide"));
    const previous = flipbook.querySelector("[data-flipbook-previous]");
    const next = flipbook.querySelector("[data-flipbook-next]");
    const status = flipbook.querySelector("[data-flipbook-status]");
    if (slides.length < 2 || !previous || !next || !status) return;
    let current = 0;
    flipbook.classList.add("is-enhanced");
    const showSlide = (index) => {
      current = Math.max(0, Math.min(index, slides.length - 1));
      slides.forEach((slide, slideIndex) => {
        const active = slideIndex === current;
        slide.hidden = !active;
        slide.setAttribute("aria-hidden", String(!active));
        slide.dataset.active = String(active);
      });
      previous.disabled = current === 0;
      next.disabled = current === slides.length - 1;
      status.textContent = `${current + 1} of ${slides.length}`;
    };
    const api = { slides, showSlide, getCurrent: () => current };
    flipbookApis.set(flipbook, api);
    previous.addEventListener("click", () => showSlide(current - 1));
    next.addEventListener("click", () => showSlide(current + 1));
    flipbook.addEventListener("keydown", (event) => {
      const interactive = event.target instanceof Element ? event.target.closest(nestedInteractiveSelector) : null;
      if (interactive) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        showSlide(current - 1);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        showSlide(current + 1);
      } else if (event.key === "Home") {
        event.preventDefault();
        showSlide(0);
      } else if (event.key === "End") {
        event.preventDefault();
        showSlide(slides.length - 1);
      }
    });
    showSlide(0);
  });

  const portfolioMedia = Array.from(document.querySelectorAll("video, audio"));
  portfolioMedia.forEach((media) => {
    media.addEventListener("play", () => {
      portfolioMedia.forEach((other) => {
        if (other !== media && !other.paused) other.pause();
      });
    });
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) portfolioMedia.forEach((media) => media.pause());
  });

  const evidenceTriggers = Array.from(document.querySelectorAll("a.evidence-trigger[href]"));
  if (!evidenceTriggers.length || typeof HTMLDialogElement === "undefined") return;

  const dialog = document.createElement("dialog");
  dialog.className = "evidence-dialog";
  dialog.setAttribute("aria-label", "Full-resolution evidence viewer");
  dialog.innerHTML = `
    <div class="evidence-dialog__surface">
      <header class="evidence-dialog__header">
        <button class="evidence-dialog__back" type="button" data-dialog-back>← Back to case study</button>
        <button class="evidence-dialog__close" type="button" data-dialog-close aria-label="Close full-resolution evidence viewer">×</button>
      </header>
      <div class="evidence-dialog__toolbar" aria-label="Image zoom controls">
        <button type="button" data-dialog-zoom-out>− <span class="visually-hidden">Zoom out</span></button>
        <button type="button" data-dialog-fit>Fit image</button>
        <button type="button" data-dialog-zoom-in>+ <span class="visually-hidden">Zoom in</span></button>
        <span class="evidence-dialog__zoom-status" data-dialog-zoom-status aria-live="polite">Fit</span>
      </div>
      <div class="evidence-dialog__canvas" data-dialog-canvas tabindex="0">
        <p class="evidence-dialog__loading" data-dialog-loading role="status">Loading full-resolution image…</p>
        <img data-dialog-image alt="">
      </div>
      <div class="evidence-dialog__caption"><h2 data-dialog-title></h2><p data-dialog-caption></p></div>
      <nav class="evidence-dialog__navigation" data-dialog-navigation aria-label="Evidence image navigation">
        <button type="button" data-dialog-previous>← Previous</button>
        <span data-dialog-position aria-live="polite"></span>
        <button type="button" data-dialog-next>Next →</button>
      </nav>
    </div>`;
  document.body.append(dialog);

  const backButton = dialog.querySelector("[data-dialog-back]");
  const closeButton = dialog.querySelector("[data-dialog-close]");
  const canvas = dialog.querySelector("[data-dialog-canvas]");
  const image = dialog.querySelector("[data-dialog-image]");
  const loading = dialog.querySelector("[data-dialog-loading]");
  const title = dialog.querySelector("[data-dialog-title]");
  const caption = dialog.querySelector("[data-dialog-caption]");
  const navigation = dialog.querySelector("[data-dialog-navigation]");
  const previous = dialog.querySelector("[data-dialog-previous]");
  const next = dialog.querySelector("[data-dialog-next]");
  const position = dialog.querySelector("[data-dialog-position]");
  const zoomIn = dialog.querySelector("[data-dialog-zoom-in]");
  const zoomOut = dialog.querySelector("[data-dialog-zoom-out]");
  const fit = dialog.querySelector("[data-dialog-fit]");
  const zoomStatus = dialog.querySelector("[data-dialog-zoom-status]");

  let opener = null;
  let activeTrigger = null;
  let activeGroup = [];
  let activeIndex = -1;
  let savedScrollY = 0;
  let fitWidth = 0;
  let fitHeight = 0;
  let zoom = 1;
  let touchStartX = null;

  const modalUrl = (trigger) => {
    const url = new URL(window.location.href);
    url.hash = `evidence=${encodeURIComponent(trigger.getAttribute("href"))}`;
    return url.toString();
  };
  const triggerForHref = (href) => evidenceTriggers.find((trigger) => trigger.getAttribute("href") === href);
  const groupForTrigger = (trigger) => {
    const flipbook = trigger.closest("[data-flipbook]");
    return flipbook ? Array.from(flipbook.querySelectorAll(".flipbook__slide .evidence-trigger")) : [trigger];
  };
  const syncFlipbook = (trigger) => {
    const flipbook = trigger.closest("[data-flipbook]");
    const slide = trigger.closest(".flipbook__slide");
    const api = flipbook ? flipbookApis.get(flipbook) : null;
    if (api && slide) api.showSlide(api.slides.indexOf(slide));
  };
  const updateZoom = (nextZoom) => {
    zoom = Math.max(0.5, Math.min(4, nextZoom));
    image.style.width = `${Math.max(1, Math.round(fitWidth * zoom))}px`;
    image.style.height = `${Math.max(1, Math.round(fitHeight * zoom))}px`;
    zoomStatus.textContent = zoom === 1 ? "Fit" : `${Math.round(zoom * 100)}%`;
    zoomOut.disabled = zoom <= 0.5;
    zoomIn.disabled = zoom >= 4;
  };
  const fitImage = () => {
    if (!image.naturalWidth || !image.naturalHeight) return;
    const availableWidth = Math.max(1, canvas.clientWidth - 32);
    const availableHeight = Math.max(1, canvas.clientHeight - 32);
    const ratio = Math.min(1, availableWidth / image.naturalWidth, availableHeight / image.naturalHeight);
    fitWidth = image.naturalWidth * ratio;
    fitHeight = image.naturalHeight * ratio;
    canvas.scrollTo(0, 0);
    updateZoom(1);
  };
  const loadTrigger = (trigger, replaceHistory = false) => {
    activeTrigger = trigger;
    activeGroup = groupForTrigger(trigger);
    activeIndex = activeGroup.indexOf(trigger);
    syncFlipbook(trigger);
    title.textContent = trigger.dataset.evidenceTitle || trigger.querySelector("img")?.alt || "Evidence image";
    caption.textContent = trigger.dataset.evidenceCaption || "";
    navigation.hidden = activeGroup.length < 2;
    previous.disabled = activeIndex <= 0;
    next.disabled = activeIndex >= activeGroup.length - 1;
    position.textContent = activeGroup.length > 1 ? `${activeIndex + 1} of ${activeGroup.length}` : "";
    loading.hidden = false;
    image.hidden = true;
    image.alt = trigger.querySelector("img")?.alt || title.textContent;
    image.removeAttribute("style");
    const requestedHref = trigger.href;
    image.onload = () => {
      if (image.src !== requestedHref) return;
      loading.hidden = true;
      image.hidden = false;
      fitImage();
    };
    image.onerror = () => {
      loading.textContent = "The full-resolution image could not be loaded.";
      image.hidden = true;
    };
    image.src = requestedHref;
    if (replaceHistory && history.state?.portfolioEvidenceModal) {
      history.replaceState({ ...history.state, evidenceHref: trigger.getAttribute("href") }, "", modalUrl(trigger));
    }
  };
  const openDialog = (trigger, pushHistory = true) => {
    if (!dialog.open) {
      opener = trigger;
      savedScrollY = window.scrollY;
      document.body.classList.add("modal-open");
      dialog.showModal();
      window.requestAnimationFrame(() => backButton.focus());
    }
    loadTrigger(trigger, false);
    if (pushHistory) {
      history.pushState({ ...(history.state || {}), portfolioEvidenceModal: true, evidenceHref: trigger.getAttribute("href") }, "", modalUrl(trigger));
    }
  };
  const closeDialog = () => {
    if (!dialog.open) return;
    dialog.close();
    document.body.classList.remove("modal-open");
    const restoreTarget = opener;
    activeTrigger = null;
    activeGroup = [];
    activeIndex = -1;
    if (restoreTarget?.isConnected) restoreTarget.focus({ preventScroll: true });
    window.scrollTo(0, savedScrollY);
  };
  const requestClose = () => {
    if (!dialog.open) return;
    if (history.state?.portfolioEvidenceModal) history.back();
    else closeDialog();
  };
  const move = (offset) => {
    const candidate = activeGroup[activeIndex + offset];
    if (candidate) loadTrigger(candidate, true);
  };

  evidenceTriggers.forEach((trigger) => {
    trigger.addEventListener("click", (event) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      openDialog(trigger, true);
    });
  });
  backButton.addEventListener("click", requestClose);
  closeButton.addEventListener("click", requestClose);
  previous.addEventListener("click", () => move(-1));
  next.addEventListener("click", () => move(1));
  zoomIn.addEventListener("click", () => updateZoom(zoom + 0.25));
  zoomOut.addEventListener("click", () => updateZoom(zoom - 0.25));
  fit.addEventListener("click", fitImage);
  canvas.addEventListener("touchstart", (event) => {
    touchStartX = event.changedTouches[0]?.clientX ?? null;
  }, { passive: true });
  canvas.addEventListener("touchend", (event) => {
    if (touchStartX === null || activeGroup.length < 2) return;
    const distance = (event.changedTouches[0]?.clientX ?? touchStartX) - touchStartX;
    touchStartX = null;
    if (Math.abs(distance) < 50) return;
    move(distance < 0 ? 1 : -1);
  }, { passive: true });
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    requestClose();
  });
  dialog.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      requestClose();
      return;
    }
    const interactive = event.target instanceof Element ? event.target.closest(nestedInteractiveSelector) : null;
    if (!interactive && activeGroup.length > 1 && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
      event.preventDefault();
      move(event.key === "ArrowLeft" ? -1 : 1);
      return;
    }
    if (event.key === "Tab") {
      const focusable = Array.from(dialog.querySelectorAll('button:not([disabled]):not([hidden]), [href], [tabindex]:not([tabindex="-1"])')).filter((element) => !element.closest("[hidden]"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
  window.addEventListener("resize", () => {
    if (dialog.open) fitImage();
  });
  window.addEventListener("popstate", (event) => {
    if (event.state?.portfolioEvidenceModal) {
      const trigger = triggerForHref(event.state.evidenceHref);
      if (trigger) openDialog(trigger, false);
    } else if (dialog.open) {
      closeDialog();
    }
  });
})();
