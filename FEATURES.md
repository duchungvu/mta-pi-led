# Features Roadmap

## Product Build Order

1. MTA LED board (first)
2. Web app for station list/status (second)
3. Mobile app controller for board content (last)

## DONE

- MTA LED board shows real-time train arrivals on the panel.
- Board supports config-driven primary station via `config/board.json` (first station currently used at runtime).
- Existing operational workflow is in place (`scripts/start-display.sh`, `scripts/stop-display.sh`, `scripts/pi-sync.sh`).
- Added runtime board config file at `config/board.json` for station/refresh/rotation/Citi Bike settings.
- Renamed main display runtime entrypoint to `src/led_board.py` (legacy wrapper kept at `src/image_display.py`).
- Phase 1 repo baseline completed:
  - Added package root at `src/mta_pi_led/`
  - Moved Citi Bike service into `src/mta_pi_led/services/citibike.py`
  - Kept legacy compatibility via `citibike/citibike.py`

## IN PROGRESS

- Reorganizing repo/module boundaries for cleaner service/API/display separation.
- Building line/station rotation behavior on top of `config/board.json`.

## TO DO

- MTA board:
  - Use full `stations` list from `config/board.json` (current runtime uses only the first station).
  - Support multiple lines for a station by rotating the displayed line every 10 seconds.
  - Define and implement rotation behavior for multiple stations on one board.
- Web app:
  - Show a list of station statuses.
  - Default to nearest station on first load.
  - Allow users to add stations later.
  - Persist selected stations in browser storage (cookie/localStorage).
- Mobile app (last phase):
  - Control what appears on the LED board.
  - Primary control: pick which stations are shown.
