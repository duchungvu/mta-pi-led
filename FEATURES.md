# Features Roadmap

## Product Build Order

1. MTA LED board (first)
2. Web app for station list/status (second)
3. Mobile app controller for board content (last)

## DONE

- MTA LED board shows real-time train arrivals on the panel.
- Board currently runs with static defaults in code (`57 St`, `F/M` preference in config).
- Existing operational workflow is in place (`scripts/start-display.sh`, `scripts/stop-display.sh`, `scripts/pi-sync.sh`).
- Phase 1 repo baseline completed:
  - Added package root at `src/mta_pi_led/`
  - Moved Citi Bike service into `src/mta_pi_led/services/citibike.py`
  - Kept legacy compatibility via `citibike/citibike.py`

## IN PROGRESS

- Reorganizing repo/module boundaries for cleaner service/API/display separation.
- Preparing MTA board logic to support configurable stations/lines (instead of hardcoded defaults).

## TO DO

- MTA board:
  - Configure board by station code input (not hardcoded station/line).
  - Support multiple lines for a station by rotating the displayed line every 10 seconds.
  - Define approach for multiple stations on one board (TBD).
- Web app:
  - Show a list of station statuses.
  - Default to nearest station on first load.
  - Allow users to add stations later.
  - Persist selected stations in browser storage (cookie/localStorage).
- Mobile app (last phase):
  - Control what appears on the LED board.
  - Primary control: pick which stations are shown.
