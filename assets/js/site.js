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
    if (meta) {
      meta.content = theme === "light" ? "#f4f0e8" : "#0b0f14";
    }
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
        // The selected theme still applies for this page when storage is unavailable.
      }
    }
  };

  const initialTheme = root.dataset.theme === "light" ? "light" : "dark";
  applyTheme(initialTheme);

  const themeToggle = document.querySelector("[data-theme-toggle]");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      applyTheme(root.dataset.theme === "dark" ? "light" : "dark", true);
    });
  }

  colourScheme.addEventListener("change", (event) => {
    if (!savedTheme()) {
      applyTheme(event.matches ? "light" : "dark");
    }
  });

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

    previous.addEventListener("click", () => showSlide(current - 1));
    next.addEventListener("click", () => showSlide(current + 1));
    flipbook.addEventListener("keydown", (event) => {
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
})();
