# Web Controller Plan

## Goal

The web app is the controller for what appears on the LED board.
The board and web app must use the same source of truth (`config/board.json`) and the same schedule derivation logic.

## Core Functionality

1. Configure board content:
   - Station list (ordered)
   - Rotation interval (`rotation_seconds`)
   - Refresh interval (`refresh_seconds`)
2. Preview exact board sequence:
   - Derived `(station_id, route_id)` schedule in display order
3. Validate and apply config safely:
   - Reject invalid station ids
   - Use config `version` to avoid overwriting stale edits
4. Show board runtime health:
   - Current view and last render timestamp (heartbeat file)
5. Show arrivals for configured stations:
   - Debug/info panel tied to configured stations

## API Baseline (Implemented)

- `GET /api/stations`
  - Query: optional `q` search string
  - Returns station id, name, and lines
- `GET /api/board/config`
  - Returns normalized config + warnings + schedule preview
- `PUT /api/board/config`
  - Validates and writes config
  - Uses `version` optimistic locking (`409` on mismatch)
- `GET /api/board/schedule`
  - Returns derived schedule preview from current config
- `GET /api/board/status`
  - Returns heartbeat payload if available, else `status=unknown`

## Config Contract

```json
{
  "version": 1,
  "stations": ["B10", "127", "A28"],
  "rotation_seconds": 5,
  "refresh_seconds": 30,
  "citibike_station_id": "66dbc551-0aca-11e7-82f6-3863bb44ef7c"
}
```

## Incremental Build Steps

1. API baseline (done)
   - Keep this stable for frontend iteration.
2. Controller UI (next)
   - Station picker, ordered list, interval fields
   - Save button wired to `PUT /api/board/config`
   - Schedule preview panel from `/api/board/schedule`
3. Runtime status integration
   - `led_board.py` writes heartbeat JSON periodically
   - Web status panel reads `/api/board/status`
4. Arrivals debug panel
   - Show station arrivals for configured stations
   - Add manual refresh + auto refresh
5. Mobile-ready extension
   - Reuse the same control API for mobile app later

## Non-Goals (for now)

- User auth/accounts
- Remote multi-user conflict resolution beyond simple version locking
- Full board-render simulation in browser
