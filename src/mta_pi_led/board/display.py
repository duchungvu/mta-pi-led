"""LED matrix display implementation."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mta_pi_led.board.settings import Config, RGB_MATRIX_BINDINGS_PATH
from mta_pi_led.services.mta_arrivals import get_train_status
from station_data import get_station_name, is_valid_station

SRC_DIR = Path(__file__).resolve().parents[2]
_RGBMATRIX_BINDINGS: tuple[Any, Any, Any] | None = None
_IMAGE_MODULE: Any | None = None


def _load_rgbmatrix_bindings() -> tuple[Any, Any, Any]:
    """Load Pi-only RGB matrix bindings on demand."""
    global _RGBMATRIX_BINDINGS
    if _RGBMATRIX_BINDINGS is None:
        if RGB_MATRIX_BINDINGS_PATH not in sys.path:
            sys.path.append(RGB_MATRIX_BINDINGS_PATH)
        from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

        _RGBMATRIX_BINDINGS = (RGBMatrix, RGBMatrixOptions, graphics)
    return _RGBMATRIX_BINDINGS


def _load_image_module() -> Any:
    """Load Pillow on demand so board runtime can be imported locally."""
    global _IMAGE_MODULE
    if _IMAGE_MODULE is None:
        from PIL import Image

        _IMAGE_MODULE = Image
    return _IMAGE_MODULE


class MTALEDDisplay:
    """Real-time MTA LED display with route icons."""

    def __init__(self, station_id: str = Config.MTA.STATION):
        self._RGBMatrix, self._RGBMatrixOptions, self._graphics = (
            _load_rgbmatrix_bindings()
        )
        self._image = _load_image_module()

        self.station_id = self._validate_station(station_id)
        self.route_icon_cache: Dict[str, Any] = {}
        self._station_scroll_station_id = self.station_id
        self._station_scroll_index = 0
        self._station_scroll_last_update = time.time()
        self._preload_route_icons()

        self.matrix = self._setup_matrix()
        self.canvas = self.matrix.CreateFrameCanvas()
        self.font = self._load_font()

        print(
            f"✓ Display initialized for {get_station_name(self.station_id)} "
            f"({self.station_id})"
        )

    def _validate_station(self, station_id: str) -> str:
        """Validate station ID and return valid ID."""
        if is_valid_station(station_id):
            return station_id

        print(f"✗ Invalid station ID: {station_id}, using default")
        return Config.MTA.STATION

    def set_station(self, station_id: str):
        """Switch active station for fetching/rendering."""
        validated_station = self._validate_station(station_id)
        if validated_station != self.station_id:
            self.station_id = validated_station
            self._station_scroll_station_id = self.station_id
            self._station_scroll_index = 0
            self._station_scroll_last_update = time.time()
            print(
                f"🔁 Switching station to {get_station_name(self.station_id)} "
                f"({self.station_id})"
            )

    def _setup_matrix(self) -> Any:
        """Configure and initialize LED matrix."""
        options = self._RGBMatrixOptions()
        options.rows = Config.Hardware.ROWS
        options.cols = Config.Hardware.COLS
        options.hardware_mapping = Config.Hardware.MAPPING
        options.gpio_slowdown = Config.Hardware.GPIO_SLOWDOWN
        options.brightness = Config.Hardware.BRIGHTNESS

        matrix = self._RGBMatrix(options=options)
        print("✓ LED matrix initialized")
        return matrix

    def _load_font(self) -> Optional[Any]:
        """Load display font."""
        try:
            font = self._graphics.Font()
            font.LoadFont(self._resolve_asset_path(Config.Files.FONT))
            print("✓ Font loaded")
            return font
        except Exception as e:
            print(f"✗ Font loading failed: {e}")
            return None

    def _resolve_asset_path(self, path_str: str) -> str:
        """Resolve asset path against src/ directory."""
        candidate = Path(path_str).expanduser()
        if not candidate.is_absolute():
            candidate = (SRC_DIR / candidate).resolve()
        return str(candidate)

    def _get_resample_mode(self) -> Any:
        """Return Pillow resampling mode compatible with installed version."""
        if hasattr(self._image, "Resampling"):
            return self._image.Resampling.LANCZOS
        return self._image.LANCZOS

    def _get_route_icon_candidates(self, route: str) -> List[str]:
        """Return ordered icon path candidates for given route."""
        route_key = (route or "").strip().upper()
        if not route_key:
            return []

        icons = getattr(Config.Files, "ROUTE_ICONS", {})
        candidates: List[str] = []

        if route_key in icons:
            candidates.append(icons[route_key])

        candidates.append(f"../icons/{route_key}.png")
        candidates.append(f"../icons/{route_key}_black.png")

        resolved_candidates: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            resolved = self._resolve_asset_path(candidate)
            if resolved in seen:
                continue
            seen.add(resolved)
            resolved_candidates.append(resolved)
        return resolved_candidates

    def _preload_route_icons(self):
        """Load available route icons into memory before runtime rendering."""
        icons_dir = (SRC_DIR / "../icons").resolve()
        resample_mode = self._get_resample_mode()

        if icons_dir.is_dir():
            for icon_path in icons_dir.glob("*.png"):
                route_key = icon_path.stem.replace("_black", "").strip().upper()
                if not route_key or route_key in self.route_icon_cache:
                    continue
                try:
                    image = self._image.open(icon_path).convert("RGB")
                    image = image.resize(Config.Layout.ICON_SIZE, resample_mode)
                    self.route_icon_cache[route_key] = image
                except Exception:
                    continue

        icon_map = getattr(Config.Files, "ROUTE_ICONS", {})
        for route_key, raw_path in icon_map.items():
            normalized_route = str(route_key).strip().upper()
            if not normalized_route or normalized_route in self.route_icon_cache:
                continue
            try:
                resolved = self._resolve_asset_path(raw_path)
                image = self._image.open(resolved).convert("RGB")
                image = image.resize(Config.Layout.ICON_SIZE, resample_mode)
                self.route_icon_cache[normalized_route] = image
            except Exception:
                continue

    def _display_line_logo(self, route: str, position: Tuple[int, int]) -> bool:
        """Load and display route icon at specified position."""
        route_key = (route or "").strip().upper()
        if route_key in self.route_icon_cache:
            self.canvas.SetImage(self.route_icon_cache[route_key], position[0], position[1])
            return True

        icon_candidates = self._get_route_icon_candidates(route)
        if not icon_candidates:
            return False

        last_error: Optional[Exception] = None
        resample_mode = self._get_resample_mode()
        for icon_path in icon_candidates:
            try:
                image = self._image.open(icon_path)
                image = image.resize(Config.Layout.ICON_SIZE, resample_mode)
                image = image.convert("RGB")
                self.route_icon_cache[route_key] = image
                self.canvas.SetImage(image, position[0], position[1])
                return True
            except Exception as exc:
                last_error = exc
                continue

        if last_error is not None:
            print(f"✗ Error displaying route icon for {route}: {last_error}")
        return False

    def _draw_route_fallback(self, route: str):
        """Draw route text when no icon asset exists."""
        text = route[:2].upper()
        x = Config.Layout.ICON_POSITION[0] + 2
        y = Config.Layout.ICON_POSITION[1] + Config.Layout.CHAR_HEIGHT
        self._draw_text(text, (x, y), Config.Colors.WHITE)

    def _get_station_name_window(self) -> str:
        """Get station name text window; scroll if it exceeds visible width."""
        station_name = get_station_name(self.station_id)
        visible_chars = Config.Display.STATION_NAME_VISIBLE_CHARS
        if self._station_scroll_station_id != self.station_id:
            self._station_scroll_station_id = self.station_id
            self._station_scroll_index = 0
            self._station_scroll_last_update = time.time()

        if len(station_name) <= visible_chars:
            self._station_scroll_index = 0
            self._station_scroll_last_update = time.time()
            return station_name

        gap = max(1, Config.Display.STATION_NAME_SCROLL_GAP)
        scroll_step = max(0.1, Config.Display.STATION_NAME_SCROLL_STEP_SECONDS)
        cycle_text = station_name + (" " * gap)

        now = time.time()
        elapsed = now - self._station_scroll_last_update
        if elapsed >= scroll_step:
            steps = int(elapsed / scroll_step)
            self._station_scroll_index = (
                self._station_scroll_index + steps
            ) % len(cycle_text)
            self._station_scroll_last_update += steps * scroll_step

        rolling_text = cycle_text + cycle_text
        return rolling_text[
            self._station_scroll_index : self._station_scroll_index + visible_chars
        ]

    def _format_single_time(self, time_str: str) -> str:
        """Format a single arrival time to fit in 3 characters."""
        if not time_str or time_str == "No data":
            return "---"

        formatted = time_str.replace(" min", "m").replace("Now", "NOW")

        if len(formatted) > Config.Display.TIME_MAX_CHARS:
            formatted = formatted.replace("m", "")[: Config.Display.TIME_MAX_CHARS]

        return formatted

    def _draw_text(
        self,
        text: str,
        position: Tuple[int, int],
        color: Tuple[int, int, int],
    ):
        """Draw text at specified position with color."""
        if self.font:
            self._graphics.DrawText(
                self.canvas,
                self.font,
                position[0],
                position[1],
                self._graphics.Color(*color),
                text,
            )

    def get_realtime_data(
        self,
        routes: Sequence[str],
        station_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], List[str], List[str]]:
        """Fetch real-time MTA data for preferred routes."""
        if isinstance(routes, str):
            routes_to_check = [routes]
        else:
            routes_to_check = list(routes or [])

        if not routes_to_check:
            print("✗ No routes configured")
            return None, [], []

        try:
            data = station_data
            if data is None:
                print(
                    f"🔄 Refreshing station feed for "
                    f"{get_station_name(self.station_id)}..."
                )
                data = get_train_status(self.station_id)

            if data.get("status") != "success":
                print("✗ Train API returned error status")
                return None, [], []

            trains = data.get("trains", {})
            fallback_route = None
            fallback_times = ([], [])

            for route in routes_to_check:
                if route not in trains:
                    continue

                route_data = trains[route]
                uptown = route_data.get("uptown", {}).get("next_arrivals", [])
                downtown = route_data.get("downtown", {}).get("next_arrivals", [])

                if fallback_route is None:
                    fallback_route = route
                    fallback_times = (uptown, downtown)

                if uptown or downtown:
                    print(f"✓ {route} Uptown: {uptown} | Downtown: {downtown}")
                    return route, uptown, downtown
                else:
                    print(f"⚠️ {route} listed but no arrivals reported")

            if fallback_route:
                print(f"⚠️ Using {fallback_route} with empty arrivals")
                return fallback_route, fallback_times[0], fallback_times[1]

            print("✗ Preferred routes not present in feed response")
            return None, [], []

        except Exception as e:
            print(f"✗ Error: {e}")
            return None, [], []

    def _draw_station_info(
        self,
        route: str,
        station_name_window: Optional[str] = None,
    ):
        """Draw station information: line logo + station name."""
        self.clear_area(Config.Layout.ICON_POSITION, Config.Layout.ICON_SIZE)
        station_clear_width = (
            Config.Display.STATION_NAME_VISIBLE_CHARS * Config.Layout.CHAR_WIDTH
        )
        station_clear_top = max(
            0,
            Config.Layout.STATION_NAME_POSITION[1] - Config.Layout.CHAR_HEIGHT - 1,
        )
        station_clear_height = Config.Layout.CHAR_HEIGHT + 2
        self.clear_area(
            (
                Config.Layout.STATION_NAME_POSITION[0],
                station_clear_top,
            ),
            (station_clear_width, station_clear_height),
        )

        if not self._display_line_logo(route, Config.Layout.ICON_POSITION):
            print(f"⚠️ Icon unavailable for route {route}; using text fallback")
            self._draw_route_fallback(route)

        if station_name_window is None:
            station_name_window = self._get_station_name_window()
        self._draw_text(
            station_name_window,
            Config.Layout.STATION_NAME_POSITION,
            Config.Colors.WHITE,
        )

    def clear_area(self, position: Tuple[int, int], size: Tuple[int, int]):
        """Clear an area of the canvas."""
        for col in range(position[0], position[0] + size[0]):
            for row in range(position[1], position[1] + size[1]):
                if 0 <= col < Config.Hardware.COLS and 0 <= row < Config.Hardware.ROWS:
                    self.canvas.SetPixel(col, row, 0, 0, 0)

    def _draw_direction_label(
        self,
        direction_name: str,
        label_position: Tuple[int, int],
    ):
        """Draw direction label (static)."""
        self._draw_text(direction_name, label_position, Config.Colors.WHITE)

    def _draw_time_box(
        self,
        time_str: str,
        position: Tuple[int, int],
        color: Tuple[int, int, int],
    ):
        """Draw a single arrival time in its box (clear + draw)."""
        self.clear_area(
            [position[0], position[1] - Config.Layout.CHAR_HEIGHT],
            [Config.Layout.TIME_BOX_WIDTH, Config.Layout.TIME_BOX_HEIGHT],
        )

        formatted_time = self._format_single_time(time_str)
        self._draw_text(formatted_time, position, color)

    def show_arrival_times(
        self,
        times: List[str],
        box_positions: List[Tuple[int, int]],
        color: Tuple[int, int, int],
    ):
        """Draw all arrival times for one direction (updates 3 boxes)."""
        padded_times = (times + [""] * Config.Display.ARRIVALS_PER_DIRECTION)[
            : Config.Display.ARRIVALS_PER_DIRECTION
        ]

        for time_str, position in zip(padded_times, box_positions):
            self._draw_time_box(time_str, position, color)

    def _draw_bike(self, position: Tuple[int, int], color: Tuple[int, int, int]):
        """Draw a 6x10 bike."""
        x, y = position

        icon_pattern = [
            [0, 1, 1, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 1, 1, 0, 0, 0, 0],
            [0, 1, 1, 0, 0, 1, 0, 1, 1, 0],
            [1, 0, 0, 1, 1, 1, 1, 0, 0, 1],
            [1, 0, 0, 1, 0, 0, 1, 0, 0, 1],
            [0, 1, 1, 0, 0, 0, 0, 1, 1, 0],
        ]

        for row in range(len(icon_pattern)):
            for col in range(len(icon_pattern[row])):
                if icon_pattern[row][col] == 1:
                    self.canvas.SetPixel(x + col, y + row, color[0], color[1], color[2])

    def _draw_ebike(self, position: Tuple[int, int], color: Tuple[int, int, int]):
        """Draw a plug indicator."""
        x, y = position

        icon_pattern = [
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            [1, 1, 1, 1],
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            [1, 0, 0, 0],
        ]

        for row in range(len(icon_pattern)):
            for col in range(len(icon_pattern[row])):
                if icon_pattern[row][col] == 1:
                    self.canvas.SetPixel(x + col, y + row, color[0], color[1], color[2])

    def show_mta_station_info(
        self,
        route: str,
        directions: Sequence[str],
        station_name_window: Optional[str] = None,
    ):
        """Show MTA station info."""
        self._draw_station_info(route, station_name_window=station_name_window)
        self._draw_direction_label(directions[0], Config.Layout.UPTOWN_LABEL_POSITION)
        self._draw_direction_label(
            directions[1],
            Config.Layout.DOWNTOWN_LABEL_POSITION,
        )

    def show_mta_arrival_times(
        self,
        route: str,
        uptown_times: List[str],
        downtown_times: List[str],
    ):
        """Display complete MTA board with all components."""
        uptown_positions = [
            Config.Layout.UPTOWN_TIME_1_POSITION,
            Config.Layout.UPTOWN_TIME_2_POSITION,
            Config.Layout.UPTOWN_TIME_3_POSITION,
        ]
        downtown_positions = [
            Config.Layout.DOWNTOWN_TIME_1_POSITION,
            Config.Layout.DOWNTOWN_TIME_2_POSITION,
            Config.Layout.DOWNTOWN_TIME_3_POSITION,
        ]

        self.show_arrival_times(uptown_times, uptown_positions, Config.Colors.GREEN)
        self.show_arrival_times(downtown_times, downtown_positions, Config.Colors.YELLOW)

        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def draw_citibike_icons(self):
        """Draw Citi Bike icons (not shown by default)."""
        self._draw_bike(Config.Layout.BIKE_ICON_POSITION, Config.Colors.DAZZLING_BLUE)
        self._draw_ebike(Config.Layout.EBIKE_ICON_POSITION, Config.Colors.DAZZLING_BLUE)

    def show_citibike_status(self, data: Dict[str, Any]):
        """Show Citi Bike status."""
        num_normal_bikes = max(
            0,
            data.get("num_bikes_available", 0) - data.get("num_ebikes_available", 0),
        )
        num_ebikes = max(0, data.get("num_ebikes_available", 0))

        bike_time_position = [
            Config.Layout.BIKE_ICON_POSITION[0] + 11,
            Config.Layout.BIKE_ICON_POSITION[1] + 6,
        ]
        ebike_time_position = [
            Config.Layout.EBIKE_ICON_POSITION[0] + 5,
            Config.Layout.EBIKE_ICON_POSITION[1] + 6,
        ]

        self.clear_area(
            [bike_time_position[0], bike_time_position[1] - 6],
            [Config.Layout.CHAR_WIDTH * 2, Config.Layout.CHAR_HEIGHT],
        )
        self.clear_area(
            [ebike_time_position[0], ebike_time_position[1] - 6],
            [Config.Layout.CHAR_WIDTH * 2, Config.Layout.CHAR_HEIGHT],
        )
        self._draw_text(
            f"{num_normal_bikes}",
            bike_time_position,
            Config.Colors.BLUE if num_normal_bikes > 0 else Config.Colors.RED,
        )
        self._draw_text(
            f"{num_ebikes}",
            ebike_time_position,
            Config.Colors.BLUE if num_ebikes > 0 else Config.Colors.RED,
        )

    def clear(self):
        """Clear the display."""
        self.canvas.Clear()
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
