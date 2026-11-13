/* Git2Tweet site — small, dependency-free progressive enhancements. */
(function () {
  "use strict";

  var root = document.documentElement;

  /* ------------------------------------------------------------------
     Theme toggle
     ------------------------------------------------------------------ */
  var themeButton = document.querySelector("[data-theme-toggle]");
  var darkMedia = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function effectiveTheme() {
    var explicit = root.getAttribute("data-theme");
    if (explicit === "light" || explicit === "dark") return explicit;
    return darkMedia && darkMedia.matches ? "dark" : "light";
  }

  var themeMetas = document.querySelectorAll("meta[name='theme-color']");

  function syncThemeMeta() {
    var color = effectiveTheme() === "dark" ? "#05070e" : "#f3f6fc";
    themeMetas.forEach(function (meta) {
      meta.setAttribute("content", color);
    });
  }

  function syncThemeLabel() {
    if (!themeButton) return;
    var next = effectiveTheme() === "dark" ? "light" : "dark";
    var label = "Switch to " + next + " mode";
    themeButton.setAttribute("aria-label", label);
    themeButton.setAttribute("title", label);
  }

  if (themeButton) {
    themeButton.addEventListener("click", function () {
      var next = effectiveTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try {
        localStorage.setItem("g2t-theme", next);
      } catch (error) {
        /* storage is optional */
      }
      syncThemeLabel();
      syncThemeMeta();
    });

    if (darkMedia) {
      var handleSystemTheme = function () {
        if (!root.getAttribute("data-theme")) {
          syncThemeLabel();
          syncThemeMeta();
        }
      };
      if (darkMedia.addEventListener) darkMedia.addEventListener("change", handleSystemTheme);
      else if (darkMedia.addListener) darkMedia.addListener(handleSystemTheme);
    }
    syncThemeLabel();
    syncThemeMeta();
  }

  /* ------------------------------------------------------------------
     Copy to clipboard
     ------------------------------------------------------------------ */
  var copyStatus = document.getElementById("copy-status");

  function textFrom(target) {
    var clone = target.cloneNode(true);
    clone.querySelectorAll("[data-no-copy]").forEach(function (node) {
      node.remove();
    });

    var lines = clone.querySelectorAll(".line");
    if (lines.length) {
      return Array.prototype.map
        .call(lines, function (line) { return line.textContent; })
        .join("\n")
        .trim();
    }
    return clone.textContent.trim();
  }

  function fallbackCopy(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.top = "-1000px";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    var ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (error) {
      ok = false;
    }
    area.remove();
    return ok;
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(
        function () { return true; },
        function () { return fallbackCopy(text); }
      );
    }
    return Promise.resolve(fallbackCopy(text));
  }

  document.querySelectorAll("[data-copy]").forEach(function (button) {
    var label = button.querySelector(".copy-label");
    var originalLabel = button.getAttribute("aria-label") || "Copy";
    var timer;

    button.addEventListener("click", function () {
      var target = document.querySelector(button.getAttribute("data-copy"));
      if (!target) return;

      copyText(textFrom(target)).then(function (ok) {
        if (copyStatus) {
          copyStatus.textContent = ok
            ? "Copied to clipboard."
            : "Copy failed. Select the command and copy it manually.";
        }
        if (!ok) return;

        button.classList.add("copied");
        button.setAttribute("aria-label", "Copied");
        if (label) label.textContent = "Copied";

        window.clearTimeout(timer);
        timer = window.setTimeout(function () {
          button.classList.remove("copied");
          button.setAttribute("aria-label", originalLabel);
          if (label) label.textContent = "Copy";
        }, 2000);
      });
    });
  });

  /* ------------------------------------------------------------------
     Install tabs
     ------------------------------------------------------------------ */
  document.querySelectorAll("[role='tablist']").forEach(function (tablist) {
    var tabs = Array.prototype.slice.call(tablist.querySelectorAll("[role='tab']"));

    function selectTab(index, focusTab) {
      tabs.forEach(function (tab, i) {
        var selected = i === index;
        tab.setAttribute("aria-selected", String(selected));
        tab.tabIndex = selected ? 0 : -1;
        var panel = document.getElementById(tab.getAttribute("aria-controls"));
        if (panel) panel.hidden = !selected;
      });
      if (focusTab) tabs[index].focus();
    }

    tabs.forEach(function (tab, i) {
      tab.addEventListener("click", function () { selectTab(i, false); });
      tab.addEventListener("keydown", function (event) {
        var next;
        if (event.key === "ArrowRight") next = (i + 1) % tabs.length;
        else if (event.key === "ArrowLeft") next = (i - 1 + tabs.length) % tabs.length;
        else if (event.key === "Home") next = 0;
        else if (event.key === "End") next = tabs.length - 1;
        else return;
        event.preventDefault();
        selectTab(next, true);
      });
    });
  });

  /* ------------------------------------------------------------------
     Scroll progress + sticky header state + nav highlight
     ------------------------------------------------------------------ */
  var header = document.querySelector(".site-header");
  var progress = document.querySelector("[data-progress]");
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".nav-main a[href^='#']"));
  var navSections = navLinks
    .map(function (link) {
      return { link: link, section: document.querySelector(link.getAttribute("href")) };
    })
    .filter(function (item) { return item.section; });

  function syncNav() {
    if (!navSections.length) return;
    var marker = window.scrollY + (header ? header.offsetHeight : 74) + 48;
    var active = null;

    navSections.forEach(function (item) {
      var top = item.section.getBoundingClientRect().top + window.scrollY;
      if (top <= marker) active = item.link;
    });

    navLinks.forEach(function (link) {
      if (link === active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }

  var scrollQueued = false;
  function paintScrollState() {
    var y = window.scrollY || window.pageYOffset || 0;
    if (header) header.classList.toggle("is-scrolled", y > 8);
    if (progress) {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var ratio = max > 0 ? Math.min(1, Math.max(0, y / max)) : 0;
      progress.style.transform = "scaleX(" + ratio + ")";
    }
    syncNav();
    scrollQueued = false;
  }
  function queueScrollPaint() {
    if (!scrollQueued) {
      scrollQueued = true;
      window.requestAnimationFrame(paintScrollState);
    }
  }

  window.addEventListener("scroll", queueScrollPaint, { passive: true });
  window.addEventListener("resize", queueScrollPaint);
  paintScrollState();

  /* ------------------------------------------------------------------
     Reveal on scroll
     ------------------------------------------------------------------ */
  document.querySelectorAll("[data-stagger]").forEach(function (group) {
    Array.prototype.forEach.call(group.children, function (child, index) {
      if (child.classList && child.classList.contains("reveal")) {
        child.setAttribute("data-reveal-delay", String(Math.min(index, 9) * 55));
      }
    });
  });

  var revealElements = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function showAllReveals() {
    revealElements.forEach(function (element) { element.classList.add("is-visible"); });
  }

  if (reduceMotion) {
    showAllReveals();
  } else {
    var revealQueued = false;

    function revealInView() {
      var viewportHeight = window.innerHeight || document.documentElement.clientHeight;

      revealElements.forEach(function (element) {
        if (element.classList.contains("is-visible") || element.hasAttribute("data-reveal-pending")) return;
        var rect = element.getBoundingClientRect();
        var inView = rect.top < viewportHeight * 0.94 && rect.bottom > -32;
        if (!inView) return;

        element.setAttribute("data-reveal-pending", "true");
        var delay = Number(element.getAttribute("data-reveal-delay") || 0);
        window.setTimeout(function () {
          element.classList.add("is-visible");
          element.removeAttribute("data-reveal-pending");
        }, delay);
      });

      revealQueued = false;
    }

    function queueReveal() {
      if (revealQueued) return;
      revealQueued = true;
      window.requestAnimationFrame(revealInView);
    }

    window.addEventListener("scroll", queueReveal, { passive: true });
    window.addEventListener("resize", queueReveal);
    queueReveal();
    window.setTimeout(revealInView, 500);
  }

  /* ------------------------------------------------------------------
     Live GitHub star count
     ------------------------------------------------------------------ */
  var starLink = document.querySelector("[data-gh-link]");
  var starValue = document.querySelector("[data-gh-stars]");
  var heroStarLink = document.querySelector("[data-hero-star-link]");
  var heroStarValue = document.querySelector("[data-hero-stars]");
  var heroStarLabel = document.querySelector("[data-hero-star-label]");
  var starCache;
  var starCacheFresh = false;

  function formatCount(value) {
    if (value >= 1000 && window.Intl && Intl.NumberFormat) {
      return new Intl.NumberFormat("en", {
        notation: "compact",
        maximumFractionDigits: 1
      }).format(value);
    }
    return value.toLocaleString("en");
  }

  function renderStars(value) {
    if (!Number.isFinite(value)) return;

    var starsLabel = value.toLocaleString("en") + (value === 1 ? " star" : " stars");
    if (starValue) starValue.textContent = formatCount(value);
    if (starLink) {
      starLink.setAttribute("aria-label", "GitHub repository, " + starsLabel);
      starLink.title = "GitHub · " + starsLabel;
    }

    if (heroStarValue && heroStarLabel) {
      if (value === 0) {
        heroStarValue.hidden = true;
        heroStarLabel.textContent = "Be the first to star Git2Tweet on GitHub";
      } else {
        heroStarValue.hidden = false;
        heroStarValue.textContent = formatCount(value);
        heroStarLabel.textContent = (value === 1 ? "star" : "stars") + " on GitHub · add yours";
        if (heroStarLink) {
          heroStarLink.setAttribute("aria-label", "Star Git2Tweet on GitHub, " + starsLabel + " so far");
        }
      }
    }
  }

  try {
    var cachedStars = localStorage.getItem("g2t-stars");
    if (cachedStars) {
      starCache = JSON.parse(cachedStars);
      if (starCache && Number.isFinite(Number(starCache.value))) {
        renderStars(Number(starCache.value));
        starCacheFresh = Number(starCache.saved) && Date.now() - Number(starCache.saved) < 5 * 60 * 1000;
      }
    }
  } catch (error) {
    starCache = null;
  }

  if (window.fetch && starValue && !starCacheFresh) {
    var starController = window.AbortController ? new AbortController() : null;
    var starTimeout = window.setTimeout(function () {
      if (starController) starController.abort();
    }, 8000);

    fetch("https://api.github.com/repos/Vex-15/git2tweet", {
      headers: { Accept: "application/vnd.github+json" },
      signal: starController ? starController.signal : undefined
    })
      .then(function (response) {
        if (!response.ok) throw new Error("GitHub request failed");
        return response.json();
      })
      .then(function (data) {
        var count = Number(data && data.stargazers_count);
        if (!Number.isFinite(count)) return;
        renderStars(count);
        try {
          localStorage.setItem("g2t-stars", JSON.stringify({ value: count, saved: Date.now() }));
        } catch (error) {
          /* cache is optional */
        }
      })
      .catch(function () {
        /* Keep the cached value, or the "GitHub" fallback label. */
      })
      .finally(function () {
        window.clearTimeout(starTimeout);
      });
  }

  /* ------------------------------------------------------------------
     Total PyPI downloads (ClickPy public ClickHouse endpoint)
     ------------------------------------------------------------------ */
  var downloadLink = document.querySelector("[data-pypi-download]");
  var downloadValue = document.querySelector("[data-pypi-downloads]");

  function parseDownloadCount(message) {
    if (typeof message !== "string") return NaN;
    var match = message.trim().toLowerCase().replace(/,/g, "").match(/^(\d+(?:\.\d+)?)([km])?$/);
    if (!match) return NaN;
    var value = Number(match[1]);
    if (match[2] === "k") value *= 1000;
    else if (match[2] === "m") value *= 1000000;
    return value;
  }

  function renderDownloads(value) {
    if (!downloadValue || !Number.isFinite(value)) return;
    downloadValue.textContent = formatCount(value);
    if (downloadLink) {
      downloadLink.setAttribute("aria-label", value.toLocaleString("en") + " total PyPI downloads");
      downloadLink.title = "Total PyPI downloads (via ClickPy)";
    }
  }

  var downloadCache = null;
  var downloadCacheFresh = false;

  try {
    var cachedDownloads = localStorage.getItem("g2t-clickpy-downloads");
    if (cachedDownloads) {
      downloadCache = JSON.parse(cachedDownloads);
      if (downloadCache && Number.isFinite(Number(downloadCache.value))) {
        renderDownloads(Number(downloadCache.value));
        downloadCacheFresh =
          Number(downloadCache.saved) &&
          Date.now() - Number(downloadCache.saved) < 30 * 60 * 1000;
      }
    }
  } catch (error) {
    downloadCache = null;
  }

  if (window.fetch && downloadValue && !downloadCacheFresh) {
    var downloadController = window.AbortController ? new AbortController() : null;
    var downloadTimeout = window.setTimeout(function () {
      if (downloadController) downloadController.abort();
    }, 8000);

    var clickpyQuery =
      "SELECT sum(count) AS downloads FROM pypi.pypi_downloads_per_day " +
      "WHERE project = 'git2tweet' FORMAT JSON";

    fetch(
      "https://sql-clickhouse.clickhouse.com/?user=demo&query=" + encodeURIComponent(clickpyQuery),
      { signal: downloadController ? downloadController.signal : undefined }
    )
      .then(function (response) {
        if (!response.ok) throw new Error("Downloads request failed");
        return response.json();
      })
      .then(function (data) {
        var row = data && data.data && data.data[0];
        var count = parseDownloadCount(String(row && row.downloads));
        if (!Number.isFinite(count)) return;
        renderDownloads(count);
        try {
          localStorage.setItem(
            "g2t-clickpy-downloads",
            JSON.stringify({ value: count, saved: Date.now() })
          );
        } catch (error) {
          /* cache is optional */
        }
      })
      .catch(function () {
        /* Keep the cached value, or the dash fallback. */
      })
      .finally(function () {
        window.clearTimeout(downloadTimeout);
      });
  }

  /* ------------------------------------------------------------------
     Anonymous site visit counter (Abacus, no account or cookie)
     ------------------------------------------------------------------ */
  var visitValue = document.querySelector("[data-visit-count]");
  var visitChip = document.querySelector("[data-visit-chip]");

  function isLocalPreview() {
    var host = window.location.hostname;
    return (
      window.location.protocol === "file:" ||
      host === "" ||
      host === "localhost" ||
      host === "127.0.0.1" ||
      host === "::1"
    );
  }

  if (window.fetch && visitValue) {
    var sessionKey = "g2t-visit-counted";
    var alreadyCounted = false;
    try {
      alreadyCounted = sessionStorage.getItem(sessionKey) === "1";
    } catch (error) {
      alreadyCounted = false;
    }

    var shouldCount = !isLocalPreview() && !alreadyCounted;
    var endpoint = "https://abacus.jasoncameron.dev/" +
      (shouldCount ? "hit" : "get") +
      "/vex-15.github.io/git2tweet-visits";

    var visitController = window.AbortController ? new AbortController() : null;
    var visitTimeout = window.setTimeout(function () {
      if (visitController) visitController.abort();
    }, 8000);

    fetch(endpoint, { cache: "no-store", signal: visitController ? visitController.signal : undefined })
      .then(function (response) {
        if (!response.ok) throw new Error("Counter request failed");
        return response.json();
      })
      .then(function (data) {
        var count = Number(data && data.value);
        if (!Number.isFinite(count)) throw new Error("Counter response was invalid");
        visitValue.textContent = count.toLocaleString("en");
        if (visitChip) {
          visitChip.dataset.state = "ok";
          visitChip.title = "Anonymous visit count powered by Abacus";
        }
        if (shouldCount) {
          try {
            sessionStorage.setItem(sessionKey, "1");
          } catch (error) {
            /* if storage is blocked, the counter will simply record this load */
          }
        }
      })
      .catch(function () {
        visitValue.textContent = "—";
        if (visitChip) {
          visitChip.dataset.state = "error";
          visitChip.title = "Visit count is unavailable right now";
        }
      })
      .finally(function () {
        window.clearTimeout(visitTimeout);
      });
  }

  /* The fallback in index.html removes .js if this file failed to initialize. */
  window.__g2tReady = true;
})();
