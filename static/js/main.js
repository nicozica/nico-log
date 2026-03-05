(function () {
  "use strict";

  const root = document.documentElement;
  const toggleButton = document.getElementById("theme-toggle");
  const COVER_FALLBACK_SRC = "/assets/img/blurfm-cover-default.svg";
  const NOW_UNAVAILABLE_LABEL = "No disponible";
  const COVER_CACHE_PREFIX = "cover|";
  const COVER_CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;
  const STREAM_PLAY_LABEL = "Play Blur FM";
  const STREAM_STOP_LABEL = "Stop Blur FM";
  const STREAM_PLAY_ICON = "▶";
  const STREAM_STOP_ICON = "■";
  const STREAM_FADE_IN_DURATION_MS = 1000;
  const STREAM_FADE_IN_STEP_MS = 50;
  const STREAM_TARGET_VOLUME = 1;

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);

    if (!toggleButton) {
      return;
    }

    const terminalEnabled = theme === "terminal";
    toggleButton.setAttribute("aria-pressed", String(terminalEnabled));
    toggleButton.textContent = terminalEnabled ? "Editorial" : "Terminal";
  }

  function readTheme() {
    try {
      return localStorage.getItem("portal-theme") || "editorial";
    } catch (error) {
      return "editorial";
    }
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem("portal-theme", theme);
    } catch (error) {
      // Ignore storage failures and keep behavior stateless.
    }
  }

  function cleanText(value) {
    if (value === null || value === undefined) {
      return "";
    }
    return String(value).trim();
  }

  function splitTitle(value) {
    const cleaned = cleanText(value);
    const separators = [" - ", " – ", " — "];
    for (let index = 0; index < separators.length; index += 1) {
      const separator = separators[index];
      if (cleaned.includes(separator)) {
        const parts = cleaned.split(separator);
        return {
          artist: cleanText(parts[0]),
          track: cleanText(parts.slice(1).join(separator)),
        };
      }
    }
    return { artist: "", track: cleaned };
  }

  function extractSources(payload) {
    const sources = [];
    ["sources", "mounts"].forEach(function (key) {
      const value = payload[key];
      if (Array.isArray(value)) {
        value.forEach(function (item) {
          if (item && typeof item === "object") {
            sources.push(item);
          }
        });
      }
    });

    if (payload.icestats && typeof payload.icestats === "object") {
      const sourceValue = payload.icestats.source;
      if (Array.isArray(sourceValue)) {
        sourceValue.forEach(function (item) {
          if (item && typeof item === "object") {
            sources.push(item);
          }
        });
      } else if (sourceValue && typeof sourceValue === "object") {
        sources.push(sourceValue);
      }
    }

    return sources;
  }

  function parseNowPayload(payload) {
    if (!payload || typeof payload !== "object") {
      return null;
    }

    const sourceCandidates = extractSources(payload);
    const source =
      sourceCandidates[0] ||
      (payload.now && typeof payload.now === "object" ? payload.now : payload);

    let title = cleanText(source.title || payload.title);
    let track = cleanText(source.track || source.song || payload.track || payload.song);
    let artist = cleanText(
      source.artist || source.server_name || source.dj || payload.artist || payload.server_name || payload.dj
    );

    if (title && (!track || !artist)) {
      const parsed = splitTitle(title);
      if (!artist && parsed.artist) {
        artist = parsed.artist;
      }
      if (!track) {
        track = parsed.track || title;
      }
    }

    track = track || title;
    artist = artist || "";

    if (!track) {
      return null;
    }

    if (track.toLowerCase() === "silence" || track.toLowerCase() === "silencio") {
      return null;
    }

    const url = cleanText(source.url || source.listenurl || source.server_url || payload.url || payload.listenurl);

    return {
      track: track,
      artist: artist,
      url: url,
      startedAt:
        source.started_at ||
        source.stream_start ||
        source.started ||
        source.timestamp ||
        payload.started_at ||
        payload.stream_start ||
        payload.started ||
        payload.timestamp ||
        "",
    };
  }

  function buildNowKey(artist, track) {
    const normalizedArtist = cleanText(artist).toLowerCase();
    const normalizedTrack = cleanText(track).toLowerCase();
    if (!normalizedTrack || normalizedTrack === "no disponible") {
      return "";
    }
    return normalizedArtist + "|" + normalizedTrack;
  }

  function emptyArtworkData() {
    return {
      url: "",
      album: "",
      year: "",
    };
  }

  function readYear(value) {
    const cleaned = cleanText(value);
    const match = cleaned.match(/\d{4}/);
    return match ? match[0] : "";
  }

  function readCoverCache(nowKey) {
    if (!nowKey) {
      return emptyArtworkData();
    }

    try {
      const rawValue = localStorage.getItem(COVER_CACHE_PREFIX + nowKey);
      if (!rawValue) {
        return emptyArtworkData();
      }
      const parsed = JSON.parse(rawValue);
      if (!parsed || typeof parsed !== "object") {
        return emptyArtworkData();
      }

      const url = normalizeArtworkUrl(parsed.url);
      const album = cleanText(parsed.album);
      const year = readYear(parsed.year);
      const timestamp = Number(parsed.ts || 0);
      if (!timestamp) {
        return emptyArtworkData();
      }
      if (Date.now() - timestamp > COVER_CACHE_TTL_MS) {
        localStorage.removeItem(COVER_CACHE_PREFIX + nowKey);
        return emptyArtworkData();
      }
      return { url: url, album: album, year: year };
    } catch (error) {
      return emptyArtworkData();
    }
  }

  function writeCoverCache(nowKey, artwork) {
    if (!nowKey || !artwork || typeof artwork !== "object") {
      return;
    }

    const url = normalizeArtworkUrl(artwork.url);
    const album = cleanText(artwork.album);
    const year = readYear(artwork.year);
    if (!url && !album && !year) {
      return;
    }

    try {
      localStorage.setItem(
        COVER_CACHE_PREFIX + nowKey,
        JSON.stringify({
          url: url,
          album: album,
          year: year,
          ts: Date.now(),
        })
      );
    } catch (error) {
      // Ignore storage errors and keep graceful fallback.
    }
  }

  function normalizeArtworkUrl(url) {
    const cleaned = cleanText(url);
    if (!cleaned) {
      return "";
    }
    const normalized = cleaned.replace(/\/\d+x\d+bb\./, "/300x300bb.");
    if (normalized.startsWith("//")) {
      return "https:" + normalized;
    }
    if (normalized.startsWith("http://")) {
      return "https://" + normalized.slice("http://".length);
    }
    return normalized;
  }

  function applyCover(coverNode, url) {
    if (!coverNode) {
      return;
    }
    coverNode.setAttribute("src", url || COVER_FALLBACK_SRC);
  }

  function readItunesArtwork(payload) {
    if (!payload || typeof payload !== "object") {
      return emptyArtworkData();
    }
    if (!payload.resultCount || !Array.isArray(payload.results) || !payload.results.length) {
      return emptyArtworkData();
    }
    const firstResult = payload.results[0];
    if (!firstResult || typeof firstResult !== "object") {
      return emptyArtworkData();
    }

    return {
      url: normalizeArtworkUrl(firstResult.artworkUrl100 || firstResult.artworkUrl60 || ""),
      album: cleanText(firstResult.collectionName || firstResult.collectionCensoredName || ""),
      year: readYear(firstResult.releaseDate || firstResult.releaseYear || ""),
    };
  }

  function fetchCoverFromItunes(artist, track) {
    const term = cleanText((artist || "") + " " + (track || "")).replace(/\s+/g, " ");
    if (!term) {
      return Promise.resolve("");
    }

    const query = "entity=song&limit=1&term=" + encodeURIComponent(term);
    const directEndpoint = "https://itunes.apple.com/search?" + query;
    const fallbackEndpoint = "/api/itunes-search?" + query;

    return fetch(directEndpoint, { cache: "no-store", headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("itunes search request failed");
        }
        return response.json();
      })
      .then(function (payload) {
        return readItunesArtwork(payload);
      })
      .catch(function () {
        return fetch(fallbackEndpoint, { cache: "no-store", headers: { Accept: "application/json" } })
          .then(function (response) {
            if (!response.ok) {
              throw new Error("itunes search fallback request failed");
            }
            return response.json();
          })
          .then(function (payload) {
            return readItunesArtwork(payload);
          })
          .catch(function () {
            return emptyArtworkData();
          });
      });
  }

  function applyMetaRow(rowNode, valueNode, value, options) {
    const settings = options && typeof options === "object" ? options : {};
    const cleaned = cleanText(value);
    const fallback = cleanText(settings.fallback);
    if (valueNode) {
      valueNode.textContent = cleaned || fallback;
    }
    if (rowNode) {
      rowNode.hidden = settings.hideWhenEmpty === true ? !cleaned : false;
    }
  }

  function applyArtwork(coverNode, albumRowNode, albumNode, yearRowNode, yearNode, artwork) {
    const normalizedArtwork = artwork && typeof artwork === "object" ? artwork : emptyArtworkData();
    applyCover(coverNode, normalizedArtwork.url);
    applyMetaRow(albumRowNode, albumNode, normalizedArtwork.album, { fallback: NOW_UNAVAILABLE_LABEL });
    applyMetaRow(yearRowNode, yearNode, normalizedArtwork.year, { fallback: NOW_UNAVAILABLE_LABEL });
  }

  function ensureCover(coverNode, albumRowNode, albumNode, yearRowNode, yearNode, nowKey, artist, track) {
    if (!nowKey) {
      const empty = emptyArtworkData();
      applyArtwork(coverNode, albumRowNode, albumNode, yearRowNode, yearNode, empty);
      return Promise.resolve(empty);
    }

    const cachedCover = readCoverCache(nowKey);
    if (cachedCover.url || cachedCover.album || cachedCover.year) {
      applyArtwork(coverNode, albumRowNode, albumNode, yearRowNode, yearNode, cachedCover);
      return Promise.resolve(cachedCover);
    }

    applyArtwork(coverNode, albumRowNode, albumNode, yearRowNode, yearNode, emptyArtworkData());
    return fetchCoverFromItunes(artist, track).then(function (cover) {
      if (!cover.url && !cover.album && !cover.year) {
        return emptyArtworkData();
      }
      writeCoverCache(nowKey, cover);
      return cover;
    });
  }

  function initNowPlayingCards() {
    document.querySelectorAll("[data-now-playing]").forEach(function (card) {
      if (card.dataset.nowPlayingInitialized === "true") {
        return;
      }

      const endpoint = cleanText(card.getAttribute("data-now-endpoint")) || "/api/now-playing";
      const refreshEnabled = card.getAttribute("data-now-refresh") === "true";
      if (!endpoint || !refreshEnabled) {
        return;
      }

      card.dataset.nowPlayingInitialized = "true";

      const trackNode = card.querySelector("[data-now-track]");
      const artistNode = card.querySelector("[data-now-artist]");
      const artistRowNode = card.querySelector("[data-now-artist-row]");
      const albumNode = card.querySelector("[data-now-album]");
      const albumRowNode = card.querySelector("[data-now-album-row]");
      const yearNode = card.querySelector("[data-now-year]");
      const yearRowNode = card.querySelector("[data-now-year-row]");
      const coverNode = card.querySelector("[data-now-cover]");
      let currentNowKey = buildNowKey(
        artistNode ? artistNode.textContent : "",
        trackNode ? trackNode.textContent : ""
      );

      function refreshCover(artist, track) {
        const fetchKey = currentNowKey;
        ensureCover(
          coverNode,
          albumRowNode,
          albumNode,
          yearRowNode,
          yearNode,
          fetchKey,
          artist,
          track
        ).then(function (cover) {
          if (fetchKey !== currentNowKey) {
            return;
          }
          applyArtwork(coverNode, albumRowNode, albumNode, yearRowNode, yearNode, cover);
        });
      }

      refreshCover(artistNode ? artistNode.textContent : "", trackNode ? trackNode.textContent : "");

      function applyNow(now) {
        if (trackNode) {
          trackNode.textContent = now.track;
        }
        applyMetaRow(artistRowNode, artistNode, now.artist, { hideWhenEmpty: true });

        const nextNowKey = buildNowKey(now.artist, now.track);
        if (nextNowKey !== currentNowKey) {
          currentNowKey = nextNowKey;
          refreshCover(now.artist, now.track);
        }
      }

      function refreshNow() {
        fetch(endpoint, { cache: "no-store", headers: { Accept: "application/json" } })
          .then(function (response) {
            if (!response.ok) {
              throw new Error("now-playing request failed");
            }
            return response.json();
          })
          .then(function (payload) {
            if (payload.success !== true) {
              return;
            }

            const payloadTitle = cleanText(payload.title || (payload.now && payload.now.title));
            if (!payloadTitle && !cleanText(payload.track) && !cleanText(payload.song)) {
              return;
            }

            const now = parseNowPayload(payload);
            if (now) {
              applyNow(now);
            }
          })
          .catch(function () {
            // Keep rendered build data when refresh fails.
          });
      }

      refreshNow();
      card.__nowPlayingIntervalId = window.setInterval(refreshNow, 60000);
    });
  }

  function setPlayerButtonState(button, isPlaying) {
    if (!button) {
      return;
    }

    button.textContent = isPlaying ? STREAM_STOP_ICON : STREAM_PLAY_ICON;
    button.setAttribute("aria-label", isPlaying ? STREAM_STOP_LABEL : STREAM_PLAY_LABEL);
  }

  function buildLiveStreamUrl(streamUrl) {
    const separator = streamUrl.includes("?") ? "&" : "?";
    return streamUrl + separator + "ts=" + Date.now();
  }

  function clearStreamFade(audio) {
    if (audio.__fadeInIntervalId) {
      window.clearInterval(audio.__fadeInIntervalId);
      audio.__fadeInIntervalId = 0;
    }
  }

  function runStreamFadeIn(audio) {
    clearStreamFade(audio);
    audio.volume = 0;

    const steps = Math.max(1, Math.ceil(STREAM_FADE_IN_DURATION_MS / STREAM_FADE_IN_STEP_MS));
    const volumeStep = STREAM_TARGET_VOLUME / steps;

    audio.__fadeInIntervalId = window.setInterval(function () {
      if (audio.paused || audio.ended) {
        clearStreamFade(audio);
        return;
      }

      const nextVolume = Math.min(STREAM_TARGET_VOLUME, audio.volume + volumeStep);
      audio.volume = nextVolume;

      if (nextVolume >= STREAM_TARGET_VOLUME) {
        clearStreamFade(audio);
      }
    }, STREAM_FADE_IN_STEP_MS);
  }

  function stopStreamPlayback(audio) {
    clearStreamFade(audio);
    audio.pause();
    audio.volume = STREAM_TARGET_VOLUME;
    try {
      audio.currentTime = 0;
    } catch (error) {
      // Some streams are not seekable; resetting src/load still clears buffered delay.
    }
    audio.removeAttribute("src");
    audio.load();
  }

  function startStreamPlayback(audio, streamUrl) {
    clearStreamFade(audio);
    audio.src = buildLiveStreamUrl(streamUrl);
    audio.volume = 0;
    return audio.play().then(function () {
      runStreamFadeIn(audio);
    });
  }

  function initNowPlayingPlayer() {
    document.querySelectorAll("[data-now-playing]").forEach(function (card) {
      const button = card.querySelector("[data-np-toggle]");
      const audio = card.querySelector("[data-np-audio]");
      const streamUrl = cleanText(card.getAttribute("data-now-stream-src"));

      if (!button || !audio || !streamUrl || button.dataset.playerInitialized === "true") {
        return;
      }

      button.dataset.playerInitialized = "true";
      setPlayerButtonState(button, !audio.paused);

      function syncButtonState() {
        setPlayerButtonState(button, !audio.paused);
      }

      button.addEventListener("click", function () {
        if (audio.paused) {
          startStreamPlayback(audio, streamUrl)
            .then(function () {
              syncButtonState();
            })
            .catch(function (error) {
              console.error("Failed to start Blur FM stream", error);
              stopStreamPlayback(audio);
              syncButtonState();
            });
          return;
        }

        stopStreamPlayback(audio);
        syncButtonState();
      });

      audio.addEventListener("play", syncButtonState);
      audio.addEventListener("pause", syncButtonState);
      audio.addEventListener("ended", syncButtonState);
      audio.addEventListener("error", function () {
        console.error("Blur FM stream playback error");
        stopStreamPlayback(audio);
        syncButtonState();
      });
    });
  }

  function initPageFeatures() {
    initNowPlayingCards();
    initNowPlayingPlayer();
  }

  applyTheme(readTheme());

  if (toggleButton) {
    toggleButton.addEventListener("click", function () {
      const nextTheme = root.getAttribute("data-theme") === "terminal" ? "editorial" : "terminal";
      applyTheme(nextTheme);
      saveTheme(nextTheme);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPageFeatures, { once: true });
  } else {
    initPageFeatures();
  }

  document.addEventListener("astro:page-load", initPageFeatures);
})();
