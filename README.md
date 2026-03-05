# MTA Pi LED Display

Real-time NYC subway arrivals and Citi Bike availability on a 64x32 RGB LED matrix (Adafruit bonnet/HAT) driven by a Raspberry Pi. The display loop and hardware control live in `src/led_board.py`.

## What it Shows

- MTA arrival times for one station and line (uptown/downtown columns)
- Citi Bike counts (bikes and e-bikes) for a single station
- Updates every 30 seconds on a 64x32 panel

## Hardware

- Raspberry Pi (with GPIO access)
- 64x32 RGB LED matrix panel
- Adafruit RGB Matrix bonnet/HAT (or compatible wiring)
- Stable 5V power supply sized for your panel

## Software Prereqs

- Python 3
- System packages: `git`, `python3-dev`, `python3-pillow`, `libatlas-base-dev`, `tmux`
- Python deps: `pip install -r config/requirements.txt`
- LED driver: `rpi-rgb-led-matrix` (build via `setup/setup_led.sh`)

## Setup

1) Build LED driver on the Pi  

   ```bash
   cd setup
   ./setup_led.sh
   ```

   This clones/builds `rpi-rgb-led-matrix` under `/home/hung` and installs Python bindings.

2) Install app dependencies  

   ```bash
   cd /home/hung/mta-pi-led   # adjust if cloned elsewhere
   python3 -m venv venv
   source venv/bin/activate
   pip install -r config/requirements.txt
   ```

3) Keep assets in place  
   Fonts and icons are referenced relative to `src/` (`../fonts`, `../icons`). Do not move them or adjust the paths in `src/led_board.py`.

4) Sync code to the Pi (from your dev machine)

   ```bash
   ./scripts/sync/pi-sync.sh
   ```

   This uses `rsync` + `fswatch` to mirror the repo to `${PI_USER}@${PI_HOST}:${PI_DIR}` (edit the script header for your host). Leave it running to auto-sync; stop with Ctrl+C when done.
   If you need shell access to the Pi, SSH using the configured hostname, e.g.:

   ```bash
   ssh hung@hung-rpi.local
   ```

## Configuration

- Runtime board settings live in `config/board.json`:
  - `stations`: station codes to include in station/line rotation schedule
  - `rotation_seconds`: line/station rotation interval
  - `refresh_seconds`: seconds between data refreshes
  - `citibike_station_id`: Citi Bike station ID to query
- The board runtime does one batched subway refresh pass per `refresh_seconds` across scheduled stations/routes, then rotates views from that cached snapshot.
- `led_board.py` hot-reloads `config/board.json` on the same cadence as feed refresh (`refresh_seconds`, default 30s), so config edits apply without restarting the board process.
- Hardware/layout defaults live in `src/led_board.py` (`Config.Hardware`, `Config.Layout`, colors/fonts/icons).
- `Config.Hardware`: `ROWS`, `COLS`, `BRIGHTNESS`, `GPIO_SLOWDOWN`, `MAPPING`
- `Config.Files.ROUTE_ICONS`: map of route → icon (`F` and `M` PNGs included)
- `Config.Files.FONT`: bitmap font path
- Need another route icon? Run `./scripts/tools/create_route_logo.py <ROUTE>`. If `icons/<ROUTE>.png` is missing, the script prints the official Wikimedia download link—save the file there (e.g., `icons/5.png`), then rerun to crop/flatten it in place.

Adjust these values before starting the display. Scripts now auto-detect the project root from their own location. You can still override with environment variables (for example `PROJECT_DIR`, `SESSION_NAME`, `BOARD_CONFIG_PATH`).

## Run / Stop

- Start: `./scripts/board/start.sh`  
  - Creates tmux session `mta-display`, `cd` into `src/`, and runs `sudo -u root python3 led_board.py` with `BOARD_CONFIG_PATH`.
- Stop: `./scripts/board/stop.sh`
  - Sends Ctrl+C to tmux process, closes the tmux session, and cleans orphan `led_board.py` processes.
- Restart: `./scripts/board/restart.sh`
- Attach to watch logs/output: `tmux attach -t mta-display` (Ctrl+B then D to detach)

## Script Layout

- Board runtime scripts: `scripts/board/`
- Sync scripts: `scripts/sync/`
- Utility/tools scripts (logo and data generation): `scripts/tools/`
- Web runtime scripts: `scripts/web/`

## Script Commands

- Board start: `./scripts/board/start.sh`
- Board stop: `./scripts/board/stop.sh`
- Board restart: `./scripts/board/restart.sh`
- Board view (attach tmux): `./scripts/board/view.sh`
- Pi sync: `./scripts/sync/pi-sync.sh`
- Generate route icon: `./scripts/tools/create_route_logo.py <ROUTE>`
- Rebuild station DB: `./scripts/tools/create_station_db.py`
- Start web controller app: `./scripts/web/start.sh`
- Stop web controller app: `./scripts/web/stop.sh`
- Restart web controller app: `./scripts/web/restart.sh`
- View web controller logs (attach tmux): `./scripts/web/view.sh`
  - Open `http://localhost:5000` for Controller UI v1.
  - Optional: `SESSION_NAME=mta-web`
  - Optional: `ENABLE_NGROK=1` to open a second tmux window with `ngrok http <WEB_PORT>`
  - Optional: `WEB_DEBUG=1 WEB_RELOADER=1` for Flask auto-reload during UI development

## Data Sources

- MTA GTFS feeds: URLs in `src/mta_feeds.py`; fetched in `src/app.py` via `get_train_status`.
- Citi Bike: station info/status via `src/mta_pi_led/services/citibike.py`.

## MTA GTFS-Realtime Feed Overview

- Feed updates ~every 30s and includes `tripUpdate` (upcoming stops) and `vehicle` (current position) entities per train.
- Key fields: `trip.tripId` format `HHMMSS_Route..Direction` (e.g., `141325_N..N`), `stopTimeUpdate[].stopId` ends with `N`/`S` for direction, arrival/departure times are Unix seconds.
- Example `tripUpdate` payload:

  ```json
  {
    "id": "000001N",
    "tripUpdate": {
      "trip": {
        "tripId": "141325_N..N",
        "startTime": "23:35:10",
        "startDate": "20250327",
        "routeId": "N"
      },
      "stopTimeUpdate": [
        {
          "arrival": { "time": "1743138152" },
          "departure": { "time": "1743138152" },
          "stopId": "R05N"
        }
      ]
    }
  }
  ```

- Reference: [GTFS-realtime spec](https://gtfs.org/documentation/realtime/reference) and [MTA docs](https://www.mta.info/document/134521).

## Field Descriptions

### Entity ID

- `id`: A unique identifier for each train update in the feed
- Format: Usually a combination of numbers and route letter (e.g., `000001N`)

### Trip Information

- `tripId`: Unique identifier for the train run  
  - Format: `HHMMSS_Route..Direction`  
  - Example: `141325_N..N` means it started at 14:13:25, is an N train, northbound
- `startTime`: Scheduled start time of the run (`HH:MM:SS`)
- `startDate`: Date of the run in `YYYYMMDD`
- `routeId`: Route identifier (N, R, W, 4, 5, 6, etc.)

### Stop Time Updates (tripUpdate entity)

Each stop entry contains:

- `arrival.time`: Unix timestamp when the train will arrive
- `departure.time`: Unix timestamp when it leaves
- `stopId`: Station identifier  
  - Format: `[Route][Number][Direction]`  
  - Example: `R05N` → R train, 5th station, northbound

### Vehicle Information (vehicle entity)

- `currentStopSequence`: Sequence number of the train’s current/next stop
- `currentStatus`: Train status (`STOPPED_AT`, `INCOMING_AT`, `IN_TRANSIT_TO`, `OUT_OF_SERVICE`)
- `timestamp`: Unix timestamp when the vehicle position was recorded
- `stopId`: The stop ID where the train is currently located (when provided)

## Troubleshooting

- Logs: `logs/mta_debug.log` (written each run)
- Matrix flicker/ghosting: try lowering `Config.Hardware.BRIGHTNESS` or tweaking `GPIO_SLOWDOWN`
- Nothing drawn: verify font/icon paths and that tmux session is running
- If you use a non-default location or session name, use env overrides when launching scripts (for example `PROJECT_DIR=...`, `SESSION_NAME=...`, `BOARD_CONFIG_PATH=...`).
