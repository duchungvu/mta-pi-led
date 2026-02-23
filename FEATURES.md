# Features Roadmap

## Product Build Order

1. MTA LED board (first)
2. Web app for station list/status (second)
3. Mobile app controller for board content (last)

## DONE

- MTA LED board shows real-time train arrivals on the panel.
- Board supports config-driven station selection via `config/board.json`.
- Existing operational workflow is in place (`scripts/start-display.sh`, `scripts/stop-display.sh`, `scripts/pi-sync.sh`).
- Added runtime board config file at `config/board.json` for station/refresh/rotation/Citi Bike settings.
- Renamed main display runtime entrypoint to `src/led_board.py` (legacy wrapper kept at `src/image_display.py`).
- Added shared display scheduler service (`display_scheduler`) for station/line view rotation.
- Board rotates across configured station/line views using `rotation_seconds`, with cached arrivals keyed by `(station, line)`.
- Phase 1 repo baseline completed:
  - Added package root at `src/mta_pi_led/`
  - Moved Citi Bike service into `src/mta_pi_led/services/citibike.py`
  - Kept legacy compatibility via `citibike/citibike.py`

## IN PROGRESS

- Reorganizing repo/module boundaries for cleaner service/API/display separation.
- Using scheduler output in web debug APIs so all clients share the same active-view logic.

## TO DO

- MTA board:
  - Add per-station line priority/order control in config (instead of raw station line order).
  - Add graceful stale-data policy per view (show age/offline indicators).
- Web app:
  - Show a list of station statuses.
  - Default to nearest station on first load.
  - Allow users to add stations later.
  - Persist selected stations in browser storage (cookie/localStorage).
- Mobile app (last phase):
  - Control what appears on the LED board.
  - Primary control: pick which stations are shown.
