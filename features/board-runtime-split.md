# Board Runtime Split

## Goal

Split the board runtime out of `src/led_board.py` into focused package modules while keeping the existing Pi launch entrypoint unchanged.

## What We Are Building

- `src/led_board.py` remains the executable compatibility shim.
- `src/mta_pi_led/board/settings.py` owns board constants, aliases, and config application.
- `src/mta_pi_led/board/display.py` owns Pi matrix setup, font/icon loading, and rendering.
- `src/mta_pi_led/board/runtime.py` owns schedule/cache/reload/refresh/rotation/render loop behavior.
- Local imports should work without `rgbmatrix` or Pillow installed.

## TODO

- [x] Add board package modules with clear boundaries.
- [x] Keep `python3 led_board.py` entrypoint compatibility.
- [x] Lazy-load Pi-only display dependencies.
- [x] Add runtime tests with a fake display.
- [x] Update README and feature roadmap references.

## Progress

- Completed first split pass with no board JSON, script, or web API changes.
