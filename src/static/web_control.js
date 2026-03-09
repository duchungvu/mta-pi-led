"use strict";

const state = {
  version: 1,
  stations: [],
  stationCatalog: [],
  stationById: new Map(),
  rotationSeconds: 10,
  refreshSeconds: 30,
  citibikeStationId: "",
  schedulePreview: [],
  statusPollHandle: null,
  isSaving: false,
  saveQueued: false,
  autoSaveTimer: null,
  serverUrl: "",
  arrivalsPollHandle: null,
};

const elements = {};

function cacheElements() {
  elements.flash = document.getElementById("flash");
  elements.rotationInput = document.getElementById("rotation-seconds");
  elements.refreshInput = document.getElementById("refresh-seconds");
  elements.versionLabel = document.getElementById("config-version");
  elements.searchInput = document.getElementById("station-search");
  elements.searchResults = document.getElementById("search-results");
  elements.selectedStations = document.getElementById("selected-stations");
  elements.saveButton = document.getElementById("save-config");
  elements.schedulePreview = document.getElementById("schedule-preview");
  elements.boardStatusSummary = document.getElementById("board-status-summary");
  elements.boardStatusJson = document.getElementById("board-status-json");
  elements.connectionSetup = document.getElementById("connection-setup");
  elements.mainApp = document.getElementById("main-app");
  elements.serverUrlInput = document.getElementById("server-url");
  elements.testConnection = document.getElementById("test-connection");
  elements.skipSetup = document.getElementById("skip-setup");
  elements.setupStatus = document.getElementById("setup-status");
  elements.changeServer = document.getElementById("change-server");
  elements.connectionBanner = document.getElementById("connection-banner");
  elements.retryConnection = document.getElementById("retry-connection");
  elements.liveArrivals = document.getElementById("live-arrivals");
  elements.arrivalsUpdated = document.getElementById("arrivals-updated");
  elements.refreshArrivals = document.getElementById("refresh-arrivals");
}

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  bindSetupEvents();
  startConnectionFlow();
});

// --- Connection setup ---

function getServerUrl() {
  return localStorage.getItem("serverUrl") || "";
}

function setServerUrl(url) {
  localStorage.setItem("serverUrl", url);
  state.serverUrl = url;
}

function isRemote() {
  return state.serverUrl !== "";
}

function apiUrl(path) {
  return state.serverUrl + path;
}

function startConnectionFlow() {
  const saved = getServerUrl();
  if (saved) {
    state.serverUrl = saved;
    showMainApp();
  } else {
    showSetup(false);
  }
}

function showSetup(allowCancel) {
  elements.connectionSetup.hidden = false;
  elements.mainApp.hidden = true;
  elements.skipSetup.hidden = !allowCancel;
  elements.serverUrlInput.value = state.serverUrl;
  elements.setupStatus.textContent = "";
  elements.serverUrlInput.focus();
}

async function showMainApp() {
  elements.connectionSetup.hidden = true;
  elements.mainApp.hidden = false;
  elements.connectionBanner.hidden = true;
  bindEvents();
  try {
    await initialize();
  } catch {
    // If loading fails, show the main app with error banner so user can retry or change server
    showConnectionError();
  }
}

function bindSetupEvents() {
  elements.testConnection.addEventListener("click", async () => {
    let url = elements.serverUrlInput.value.trim().replace(/\/+$/, "");
    if (!url) {
      // Empty means same-origin (local access)
      url = "";
    }

    elements.setupStatus.textContent = "Testing connection...";
    elements.setupStatus.className = "setup-status";
    elements.testConnection.disabled = true;

    try {
      const resp = await fetch(url + "/api/ping");
      const data = await resp.json();
      if (data.status === "ok") {
        elements.setupStatus.textContent = "Connected!";
        elements.setupStatus.className = "setup-status ok";
        setServerUrl(url);
        setTimeout(() => showMainApp(), 500);
      } else {
        elements.setupStatus.textContent = "Unexpected response from server.";
        elements.setupStatus.className = "setup-status error";
      }
    } catch {
      elements.setupStatus.textContent = "Cannot reach server. Check the URL and try again.";
      elements.setupStatus.className = "setup-status error";
    } finally {
      elements.testConnection.disabled = false;
    }
  });

  elements.skipSetup.addEventListener("click", () => {
    showMainApp();
  });

  elements.changeServer.addEventListener("click", () => {
    showSetup(true);
  });

  elements.retryConnection.addEventListener("click", () => {
    elements.connectionBanner.hidden = true;
    initialize();
  });
}

function showConnectionError() {
  elements.connectionBanner.hidden = false;
}

// --- Main app ---

async function initialize() {
  try {
    await Promise.all([loadStationCatalog(), loadConfig()]);
    renderAll();
    await refreshBoardStatus();
    startStatusPolling();
    // Load arrivals after everything else is ready — the GTFS fetch can be slow
    // and blocks the single-threaded Flask server from handling other requests.
    loadArrivals().then(() => startArrivalsPolling());
  } catch (error) {
    showConnectionError();
    setFlash("error", `Failed to initialize controller: ${error.message}`);
  }
}

function bindEvents() {
  elements.searchInput.addEventListener("input", () => {
    renderSearchResults();
  });

  elements.rotationInput.addEventListener("change", () => {
    state.rotationSeconds = parsePositiveInt(elements.rotationInput.value, 10);
    renderSettings();
  });

  elements.refreshInput.addEventListener("change", () => {
    state.refreshSeconds = parsePositiveInt(elements.refreshInput.value, 30);
    renderSettings();
  });

  elements.saveButton.addEventListener("click", () => {
    saveConfig();
  });

  elements.refreshArrivals.addEventListener("click", () => {
    loadArrivals();
  });
}

async function loadStationCatalog() {
  const payload = await fetchJson("/api/stations");
  const stations = Array.isArray(payload.stations) ? payload.stations : [];

  state.stationCatalog = stations;
  state.stationById.clear();
  for (const station of stations) {
    state.stationById.set(station.station_id, station);
  }
}

async function loadConfig() {
  const payload = await fetchJson("/api/board/config");
  const config = payload.config || {};

  state.version = Number(config.version) || 1;
  state.stations = Array.isArray(config.stations) ? config.stations.slice() : [];
  state.rotationSeconds = parsePositiveInt(config.rotation_seconds, 10);
  state.refreshSeconds = parsePositiveInt(config.refresh_seconds, 30);
  state.citibikeStationId = config.citibike_station_id || "";
  state.schedulePreview = Array.isArray(payload.schedule_preview)
    ? payload.schedule_preview
    : [];

  const warnings = Array.isArray(payload.warnings) ? payload.warnings : [];
  if (warnings.length > 0) {
    setFlash("error", warnings.join(" "));
  }
}

async function saveConfig() {
  if (state.stations.length === 0) {
    setFlash("error", "Add at least one station before saving.");
    return;
  }

  const payload = {
    version: state.version,
    stations: state.stations,
    rotation_seconds: parsePositiveInt(elements.rotationInput.value, 10),
    refresh_seconds: parsePositiveInt(elements.refreshInput.value, 30),
    citibike_station_id: state.citibikeStationId,
  };

  state.isSaving = true;
  updateSaveButtonState();
  try {
    const response = await fetch(apiUrl("/api/board/config"), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();

    if (response.status === 409) {
      setFlash(
        "error",
        "Config version mismatch. Reloaded latest config; re-apply your edits."
      );
      await loadConfig();
      renderAll();
      return;
    }

    if (!response.ok) {
      const errors = Array.isArray(body.errors) ? body.errors.join(" ") : "Save failed.";
      setFlash("error", errors);
      return;
    }

    state.version = Number(body.config.version) || state.version + 1;
    state.stations = Array.isArray(body.config.stations) ? body.config.stations.slice() : state.stations;
    state.rotationSeconds = parsePositiveInt(body.config.rotation_seconds, state.rotationSeconds);
    state.refreshSeconds = parsePositiveInt(body.config.refresh_seconds, state.refreshSeconds);
    state.citibikeStationId = body.config.citibike_station_id || state.citibikeStationId;
    state.schedulePreview = Array.isArray(body.schedule_preview)
      ? body.schedule_preview
      : [];

    setFlash("ok", "Board config saved.");
    renderAll();
  } catch (error) {
    showConnectionError();
    setFlash("error", `Save failed: ${error.message}`);
  } finally {
    state.isSaving = false;
    updateSaveButtonState();
  }
}

function addStation(stationId) {
  if (!state.stationById.has(stationId)) {
    return;
  }
  if (state.stations.includes(stationId)) {
    return;
  }
  state.stations.push(stationId);
  renderStations();
  queueAutoSave();
}

function removeStation(stationId) {
  state.stations = state.stations.filter((value) => value !== stationId);
  renderStations();
  queueAutoSave();
}

function moveStation(stationId, direction) {
  const currentIndex = state.stations.indexOf(stationId);
  if (currentIndex < 0) {
    return;
  }
  const nextIndex = currentIndex + direction;
  if (nextIndex < 0 || nextIndex >= state.stations.length) {
    return;
  }

  const nextStations = state.stations.slice();
  [nextStations[currentIndex], nextStations[nextIndex]] = [
    nextStations[nextIndex],
    nextStations[currentIndex],
  ];
  state.stations = nextStations;
  renderStations();
  queueAutoSave();
}

function renderAll() {
  renderSettings();
  renderStations();
  renderSchedulePreview();
}

function renderSettings() {
  elements.rotationInput.value = String(state.rotationSeconds);
  elements.refreshInput.value = String(state.refreshSeconds);
  elements.versionLabel.textContent = `Version: ${state.version}`;
}

function renderStations() {
  renderSearchResults();
  renderSelectedStations();
  updateSaveButtonState();
}

function renderSearchResults() {
  const query = elements.searchInput.value.trim().toLowerCase();
  const filtered = state.stationCatalog
    .filter((station) => {
      if (!query) {
        return true;
      }
      const searchable = `${station.station_id} ${station.name}`.toLowerCase();
      return searchable.includes(query);
    })
    .slice(0, 20);

  elements.searchResults.innerHTML = "";
  if (filtered.length === 0) {
    elements.searchResults.appendChild(emptyItem("No stations found."));
    return;
  }

  for (const station of filtered) {
    const li = document.createElement("li");
    li.className = "item";
    li.innerHTML = `
      <div>
        <div class="name">${station.name}</div>
        <div class="meta">${station.station_id} · ${station.lines.join(", ")}</div>
      </div>
    `;

    const actionWrap = document.createElement("div");
    actionWrap.className = "item-actions";
    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.className = "secondary";
    addButton.textContent = state.stations.includes(station.station_id) ? "Added" : "Add";
    addButton.disabled = state.stations.includes(station.station_id);
    addButton.addEventListener("click", () => addStation(station.station_id));
    actionWrap.appendChild(addButton);
    li.appendChild(actionWrap);
    elements.searchResults.appendChild(li);
  }
}

function renderSelectedStations() {
  elements.selectedStations.innerHTML = "";
  if (state.stations.length === 0) {
    elements.selectedStations.appendChild(
      emptyItem("No stations selected. Add stations from search results.")
    );
    return;
  }

  for (const stationId of state.stations) {
    const station = state.stationById.get(stationId) || {
      station_id: stationId,
      name: stationId,
      lines: [],
    };
    const li = document.createElement("li");
    li.className = "item";
    li.innerHTML = `
      <div>
        <div class="name">${station.name}</div>
        <div class="meta">${station.station_id} · ${station.lines.join(", ")}</div>
      </div>
    `;

    const actions = document.createElement("div");
    actions.className = "item-actions";
    actions.appendChild(makeActionButton("↑", "secondary", () => moveStation(stationId, -1)));
    actions.appendChild(makeActionButton("↓", "secondary", () => moveStation(stationId, 1)));
    actions.appendChild(makeActionButton("Remove", "danger", () => removeStation(stationId)));
    li.appendChild(actions);
    elements.selectedStations.appendChild(li);
  }
}

function renderSchedulePreview() {
  elements.schedulePreview.innerHTML = "";
  if (state.schedulePreview.length === 0) {
    elements.schedulePreview.appendChild(emptyItem("No scheduled views."));
    return;
  }

  for (const item of state.schedulePreview) {
    const li = document.createElement("li");
    li.className = "item";
    li.innerHTML = `
      <div>
        <div class="name">${item.station_name}</div>
        <div class="meta">${item.station_id} · Line ${item.route_id}</div>
      </div>
    `;
    elements.schedulePreview.appendChild(li);
  }
}

function makeActionButton(label, className, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function emptyItem(text) {
  const li = document.createElement("li");
  li.className = "empty";
  li.textContent = text;
  return li;
}

async function refreshBoardStatus() {
  try {
    const payload = await fetchJson("/api/board/status");
    if (payload.status === "ok") {
      elements.boardStatusSummary.textContent = "Board heartbeat available.";
      elements.boardStatusJson.textContent = JSON.stringify(payload.board, null, 2);
      return;
    }
    elements.boardStatusSummary.textContent =
      payload.message || "Board heartbeat not available yet.";
    elements.boardStatusJson.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    elements.boardStatusSummary.textContent = `Board status unavailable: ${error.message}`;
    elements.boardStatusJson.textContent = "";
  }
}

function startStatusPolling() {
  if (state.statusPollHandle) {
    window.clearInterval(state.statusPollHandle);
  }
  state.statusPollHandle = window.setInterval(() => {
    refreshBoardStatus();
  }, 10000);
}

async function fetchJson(path) {
  const response = await fetch(apiUrl(path));
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function parsePositiveInt(value, fallbackValue) {
  const parsed = Number.parseInt(value, 10);
  if (Number.isFinite(parsed) && parsed > 0) {
    return parsed;
  }
  return fallbackValue;
}

function setFlash(type, message) {
  elements.flash.className = `flash ${type}`;
  elements.flash.textContent = message;
}

function updateSaveButtonState() {
  elements.saveButton.disabled = state.isSaving || state.stations.length === 0;
}

function queueAutoSave() {
  if (state.autoSaveTimer) {
    window.clearTimeout(state.autoSaveTimer);
  }
  state.autoSaveTimer = window.setTimeout(() => {
    state.autoSaveTimer = null;
    autoSaveConfig();
  }, 300);
}

async function autoSaveConfig() {
  if (state.isSaving) {
    state.saveQueued = true;
    return;
  }
  await saveConfig();
  if (state.saveQueued) {
    state.saveQueued = false;
    await saveConfig();
  }
}

// --- Live Arrivals ---

async function loadArrivals() {
  elements.refreshArrivals.disabled = true;
  try {
    const payload = await fetchJson("/api/board/arrivals");
    renderArrivals(payload);
  } catch (error) {
    elements.liveArrivals.innerHTML = '<div class="empty">Failed to load arrivals.</div>';
    elements.arrivalsUpdated.textContent = "";
  } finally {
    elements.refreshArrivals.disabled = false;
  }
}

function renderArrivals(payload) {
  const arrivals = payload.arrivals || {};
  const stationIds = Object.keys(arrivals);

  if (stationIds.length === 0) {
    elements.liveArrivals.innerHTML =
      '<div class="empty">No stations configured. Add stations to see live arrivals.</div>';
    elements.arrivalsUpdated.textContent = "";
    return;
  }

  elements.arrivalsUpdated.textContent = "Updated " + (payload.updated_at || "");

  let html = "";
  for (const stationId of stationIds) {
    const station = arrivals[stationId];
    const routes = station.trains || {};
    const routeIds = Object.keys(routes);

    html += '<div class="arrival-card">';
    html += '<div class="arrival-station-name">' + escapeHtml(station.station_name || stationId) + "</div>";

    if (station.status === "error" || routeIds.length === 0) {
      html += '<div class="empty">No trains available.</div>';
      html += "</div>";
      continue;
    }

    for (const routeId of routeIds) {
      const route = routes[routeId];
      const color = route.color || "#808080";
      const textColor = route.text_color || "#FFFFFF";
      const uptownArrivals = (route.uptown && route.uptown.next_arrivals) || [];
      const downtownArrivals = (route.downtown && route.downtown.next_arrivals) || [];

      if (uptownArrivals.length === 0 && downtownArrivals.length === 0) {
        continue;
      }

      html += '<div class="arrival-route">';
      html +=
        '<span class="line-badge" style="background:' +
        color +
        ";color:" +
        textColor +
        '">' +
        escapeHtml(routeId) +
        "</span>";
      html += '<div class="arrival-directions">';

      if (uptownArrivals.length > 0) {
        html += '<div class="arrival-direction">';
        html += '<span class="direction-label">Uptown</span>';
        html += '<div class="arrival-times">';
        for (const t of uptownArrivals) {
          html += '<span class="arrival-pill">' + escapeHtml(t) + "</span>";
        }
        html += "</div></div>";
      }

      if (downtownArrivals.length > 0) {
        html += '<div class="arrival-direction">';
        html += '<span class="direction-label">Downtown</span>';
        html += '<div class="arrival-times">';
        for (const t of downtownArrivals) {
          html += '<span class="arrival-pill">' + escapeHtml(t) + "</span>";
        }
        html += "</div></div>";
      }

      html += "</div></div>";
    }

    html += "</div>";
  }

  elements.liveArrivals.innerHTML = html;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function startArrivalsPolling() {
  if (state.arrivalsPollHandle) {
    window.clearInterval(state.arrivalsPollHandle);
  }
  state.arrivalsPollHandle = window.setInterval(() => {
    loadArrivals();
  }, state.refreshSeconds * 1000);
}

