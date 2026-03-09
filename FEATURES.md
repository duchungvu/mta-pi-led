# Features Roadmap

## Product Build Order

1. MTA LED board (first)
2. Web app for station list/status (second)
3. Mobile app controller for board content (last)

## DONE

- MTA LED board shows real-time train arrivals on the panel.
- Board supports config-driven station selection via `config/board.json`.
- Existing operational workflow is in place (`scripts/board/start.sh`, `scripts/board/stop.sh`, `scripts/sync/pi-sync.sh`).
- Added runtime board config file at `config/board.json` for station/refresh/rotation/Citi Bike settings.
- Main display runtime entrypoint is `src/led_board.py` (single runtime entrypoint).
- Added shared display scheduler service (`display_scheduler`) for station/line view rotation.
- Board rotates across configured station/line views using `rotation_seconds`, with cached arrivals keyed by `(station, line)`.
- Board performs one batched subway feed refresh pass per `refresh_seconds` for all scheduled stations/routes, then rotates from cached results.
- Board supports hot reload of `config/board.json` at runtime on refresh cadence (no process restart needed for config edits).
- Runtime loop refactored into focused helper functions + `RuntimeState` to keep scheduler/render logic maintainable.
- Station name now auto-scrolls when it exceeds available display width.
- Board skips routes with no live arrivals and retries them after refresh cooldown.
- Realtime station parsing now returns only actively running lines (lines with live arrivals), plus `active_routes` in API payloads.
- Scripts reorganized by purpose:
  - `scripts/board/` for display runtime operations
  - `scripts/web/` now supports tmux-managed start/stop/restart/view lifecycle for web controller runtime
  - `scripts/sync/` for Pi sync tooling
  - `scripts/tools/` for reusable utility scripts (including route logo generation)
- Phase 1 repo baseline completed:
  - Added package root at `src/mta_pi_led/`
  - Moved Citi Bike service into `src/mta_pi_led/services/citibike.py`
- Web controller API baseline (from-scratch) added in `src/web_control.py`:
  - `GET /api/stations` (station picker/search source)
  - `GET /api/board/config` (single source of truth config)
  - `PUT /api/board/config` (validated config writes)
  - `GET /api/board/schedule` (derived board rotation preview)
  - `GET /api/board/status` (runtime heartbeat placeholder)
- Added reusable board-control service helpers in `src/mta_pi_led/services/board_control.py`.
- Controller UI v1 implemented in `src/templates/web_control.html` + `src/static/web_control.js` + `src/static/web_control.css`:
  - Station search/add/remove with ordered list (rotation order).
  - Rotation/refresh settings form.
  - Save flow with optimistic config version handling.
  - Schedule preview panel and board status panel.
- PWA support for web controller:
  - Connection setup screen with configurable server URL.
  - Service worker with cache-first for app shell, network-first for API calls.
  - Web app manifest and icons for home screen install.
- Live Arrivals panel in web controller:
  - `GET /api/board/arrivals` endpoint returns real-time arrivals for all configured stations.
  - Arrival cards with colored MTA line badges grouped by station.
  - Auto-refresh polling keeps arrivals current.

## IN PROGRESS

- Reorganizing repo/module boundaries for cleaner service/API/display separation.
- Using scheduler output in web debug APIs so all clients share the same active-view logic.
- Building web app as board controller first (web selections must match board schedule exactly).

## TO DO

- MTA board:
  - Add per-station line priority/order control in config (instead of raw station line order).
  - Add graceful stale-data policy per view (show age/offline indicators).
- Web app:
  - Add board status heartbeat from display runtime so UI can show currently-rendered view.
  - Default to nearest station on first load (for debug panel add flow).
  - Persist station picks in browser storage (cookie/localStorage).
- Mobile app (last phase):
  - Control what appears on the LED board.
  - Primary control: pick which stations are shown.
