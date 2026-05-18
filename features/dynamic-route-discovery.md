# Dynamic Route Discovery

## Status

DONE

## Goal

Show any route that GTFS realtime says is currently stopping at a configured
station, even when the local static station database does not list that route.

## Behavior

- Static station lines remain the baseline display schedule.
- Realtime refreshes can discover additional routes by matching GTFS stop IDs
  such as `B10N` and `B10S`.
- Discovered routes are appended after static routes in sorted order.
- Discovered routes expire after two refresh intervals without live arrivals.
- Service alerts alone do not create display routes; arrivals require GTFS
  `tripUpdate.stopTimeUpdate` data.

## Verification

- Unit tests cover static route filtering, dynamic route discovery, non-matching
  stops, and static-first route ordering.
