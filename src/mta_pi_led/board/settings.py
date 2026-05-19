"""Shared board runtime settings and aliases."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from mta_pi_led.services.board_config import BoardConfig
from station_data import is_valid_station

CacheKey = Tuple[str, str]
ArrivalCacheValue = Tuple[int, List[str], List[str]]
StationFeedCacheValue = Tuple[int, Dict[str, Any]]
RenderSignature = Tuple[str, str, Tuple[str, ...], Tuple[str, ...], str]
DIRECTION_LABELS = ("UPTOWN", "DOWNTOWN")
RGB_MATRIX_BINDINGS_PATH = "/home/hung/rpi-rgb-led-matrix/bindings/python"


class Config:
    """Organized configuration for MTA LED Display."""

    class Hardware:
        """LED matrix hardware settings."""

        ROWS = 32
        COLS = 64
        BRIGHTNESS = 10
        MAPPING = "adafruit-hat"
        GPIO_SLOWDOWN = 5

    class Files:
        """File paths for fonts and icons."""

        FONT = "../fonts/4x6.bdf"
        # Optional per-route icon path overrides.
        ROUTE_ICONS: Dict[str, str] = {}

    class Layout:
        """Display layout positions and sizes."""

        ICON_SIZE = (18, 18)
        ICON_POSITION = (1, 8)

        STATION_NAME_POSITION = (1, 6)

        UPTOWN_LABEL_POSITION = (22, 6)
        UPTOWN_TIME_1_POSITION = (22, 12)
        UPTOWN_TIME_2_POSITION = (36, 12)
        UPTOWN_TIME_3_POSITION = (50, 12)

        DOWNTOWN_LABEL_POSITION = (22, 19)
        DOWNTOWN_TIME_1_POSITION = (22, 25)
        DOWNTOWN_TIME_2_POSITION = (36, 25)
        DOWNTOWN_TIME_3_POSITION = (50, 25)

        TIME_BOX_WIDTH = 12
        TIME_BOX_HEIGHT = 6

        BIKE_ICON_POSITION = (1, 26)
        EBIKE_ICON_POSITION = (21, 26)

        CHAR_WIDTH = 4
        CHAR_HEIGHT = 6

    class Colors:
        """RGB color definitions."""

        WHITE = (255, 255, 255)
        GREEN = (0, 255, 0)
        YELLOW = (255, 255, 0)
        RED = (255, 0, 0)
        DAZZLING_BLUE = (57, 80, 160)
        BLUE = (0, 0, 255)

    class Display:
        """Display behavior settings."""

        ARRIVALS_PER_DIRECTION = 3
        DYNAMIC_ROUTE_STALE_REFRESHES = 2
        STATION_NAME_VISIBLE_CHARS = 5
        STATION_NAME_SCROLL_GAP = 3
        STATION_NAME_SCROLL_STEP_SECONDS = 0.22
        ROTATION_INTERVAL = 10
        REFRESH_INTERVAL = 30
        UI_TICK_INTERVAL = 0.16
        TIME_MAX_CHARS = 3

    class MTA:
        """MTA station and route defaults."""

        STATION = "B10"
        ROUTES = ["F", "M"]

    class CitiBike:
        """Citi Bike station and route defaults."""

        ENABLED = False
        STATION_ID = "66dbc551-0aca-11e7-82f6-3863bb44ef7c"


def apply_board_config(board_config: BoardConfig):
    """Apply runtime settings loaded from board.json."""
    selected_station = board_config.primary_station
    if not is_valid_station(selected_station):
        print(
            f"⚠️ Invalid station in board config: {selected_station}. "
            f"Using default {Config.MTA.STATION}."
        )
    else:
        Config.MTA.STATION = selected_station

    Config.Display.REFRESH_INTERVAL = board_config.refresh_seconds
    Config.Display.ROTATION_INTERVAL = board_config.rotation_seconds
    Config.CitiBike.STATION_ID = board_config.citibike_station_id
