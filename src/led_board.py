#!/usr/bin/env python3
"""
Real-time MTA LED Display using PNG images for route icons
Fetches live MTA data and displays on 64x32 LED matrix with 30-second refresh
"""

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Sequence, Any

sys.path.append('/home/hung/rpi-rgb-led-matrix/bindings/python')

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Import Citi Bike data functions from package path
from mta_pi_led.services.board_config import (
    BoardConfig,
    load_board_config,
    resolve_board_config_path,
)
from mta_pi_led.services.citibike import get_station_data
from mta_pi_led.services.display_scheduler import (
    DisplaySchedule,
    DisplayView,
    create_display_schedule,
)

# Import MTA data functions
from app import get_train_status, get_train_status_batch
from station_data import get_station_lines, is_valid_station, get_station_name

CacheKey = Tuple[str, str]
ArrivalCacheValue = Tuple[int, List[str], List[str]]
StationFeedCacheValue = Tuple[int, Dict[str, Any]]
RenderSignature = Tuple[str, str, Tuple[str, ...], Tuple[str, ...], str]
DIRECTION_LABELS = ("UPTOWN", "DOWNTOWN")


# Configuration Constants
class Config:
    """Organized configuration for MTA LED Display"""
    
    class Hardware:
        """LED matrix hardware settings"""
        ROWS = 32
        COLS = 64
        BRIGHTNESS = 10
        MAPPING = 'adafruit-hat'
        GPIO_SLOWDOWN = 5
    
    class Files:
        """File paths for fonts and icons"""
        FONT = '../fonts/4x6.bdf'
        # Optional per-route icon path overrides.
        ROUTE_ICONS: Dict[str, str] = {}
    
    class Layout:
        """Display layout positions and sizes"""
        ICON_SIZE = (18, 18)
        ICON_POSITION = (1, 8)
        
        STATION_NAME_POSITION = (1, 6)
        
        # Uptown direction
        UPTOWN_LABEL_POSITION = (22, 6)
        UPTOWN_TIME_1_POSITION = (22, 12)
        UPTOWN_TIME_2_POSITION = (36, 12)
        UPTOWN_TIME_3_POSITION = (50, 12)
        
        # Downtown direction
        DOWNTOWN_LABEL_POSITION = (22, 19)
        DOWNTOWN_TIME_1_POSITION = (22, 25)
        DOWNTOWN_TIME_2_POSITION = (36, 25)
        DOWNTOWN_TIME_3_POSITION = (50, 25)
        
        # Time box dimensions
        TIME_BOX_WIDTH = 12   # 3 chars × 4px per char = 12px
        TIME_BOX_HEIGHT = 6   # Font height

        # Bike icon position
        BIKE_ICON_POSITION = (1, 26)
        EBIKE_ICON_POSITION = (21, 26)

        CHAR_WIDTH = 4
        CHAR_HEIGHT = 6
    
    class Colors:
        """RGB color definitions"""
        WHITE = (255, 255, 255)
        GREEN = (0, 255, 0)
        YELLOW = (255, 255, 0)
        RED = (255, 0, 0)
        DAZZLING_BLUE = (57, 80, 160)
        BLUE = (0, 0, 255)

    
    class Display:
        """Display behavior settings"""
        ARRIVALS_PER_DIRECTION = 3  # Show 3 arrival times per direction
        STATION_NAME_VISIBLE_CHARS = 5
        STATION_NAME_SCROLL_GAP = 3
        STATION_NAME_SCROLL_STEP_SECONDS = 0.22
        ROTATION_INTERVAL = 10
        REFRESH_INTERVAL = 30
        UI_TICK_INTERVAL = 0.16
        TIME_MAX_CHARS = 3  # Max characters per time box
    
    class MTA:
        """MTA station and route defaults"""
        STATION = "B10"  # 57th St (F/M)
        ROUTES = ["F", "M"]  # preference order

    class CitiBike:
        """Citi Bike station and route defaults"""
        ENABLED = False
        STATION_ID = "66dbc551-0aca-11e7-82f6-3863bb44ef7c"


@dataclass
class RuntimeState:
    """Mutable runtime state for the display loop."""

    schedule: DisplaySchedule
    active_index: int
    current_route: str
    next_rotation_ts: float
    last_config_reload_check_ts: int
    last_station_feed_refresh_ts: int = 0
    last_citibike_fetch_ts: int = 0
    last_render_signature: Optional[RenderSignature] = None
    arrival_cache: Dict[CacheKey, ArrivalCacheValue] = field(default_factory=dict)
    station_feed_cache: Dict[str, StationFeedCacheValue] = field(default_factory=dict)
    unavailable_until: Dict[CacheKey, int] = field(default_factory=dict)


class MTALEDDisplay:
    """Real-time MTA LED display with route icons"""
    
    def __init__(self, station_id: str = Config.MTA.STATION):
        self.station_id = self._validate_station(station_id)
        self.route_icon_cache: Dict[str, Image.Image] = {}
        self._station_scroll_station_id = self.station_id
        self._station_scroll_index = 0
        self._station_scroll_last_update = time.time()
        self._preload_route_icons()
        
        # Initialize hardware
        self.matrix = self._setup_matrix()
        self.canvas = self.matrix.CreateFrameCanvas()
        self.font = self._load_font()
        
        print(f"✓ Display initialized for {get_station_name(self.station_id)} ({self.station_id})")
    
    def _validate_station(self, station_id: str) -> str:
        """Validate station ID and return valid ID"""
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
    
    def _setup_matrix(self) -> RGBMatrix:
        """Configure and initialize LED matrix"""
        options = RGBMatrixOptions()
        options.rows = Config.Hardware.ROWS
        options.cols = Config.Hardware.COLS
        options.hardware_mapping = Config.Hardware.MAPPING
        options.gpio_slowdown = Config.Hardware.GPIO_SLOWDOWN
        options.brightness = Config.Hardware.BRIGHTNESS
        
        matrix = RGBMatrix(options=options)
        print("✓ LED matrix initialized")
        return matrix
    
    def _load_font(self) -> Optional[graphics.Font]:
        """Load display font"""
        try:
            font = graphics.Font()
            font.LoadFont(Config.Files.FONT)
            print("✓ Font loaded")
            return font
        except Exception as e:
            print(f"✗ Font loading failed: {e}")
            return None

    def _resolve_asset_path(self, path_str: str) -> str:
        """Resolve asset path against src/ directory."""
        candidate = Path(path_str).expanduser()
        if not candidate.is_absolute():
            candidate = (Path(__file__).resolve().parent / candidate).resolve()
        return str(candidate)

    def _get_resample_mode(self):
        """Return Pillow resampling mode compatible with installed version."""
        if hasattr(Image, "Resampling"):
            return Image.Resampling.LANCZOS
        return Image.LANCZOS
    
    def _get_route_icon_candidates(self, route: str) -> List[str]:
        """Return ordered icon path candidates for given route."""
        route_key = (route or "").strip().upper()
        if not route_key:
            return []

        icons = getattr(Config.Files, 'ROUTE_ICONS', {})
        candidates: List[str] = []

        if route_key in icons:
            candidates.append(icons[route_key])

        # Prefer new suffix-free filename, then legacy name for compatibility.
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
        icons_dir = (Path(__file__).resolve().parent / "../icons").resolve()
        resample_mode = self._get_resample_mode()

        # Load route icons from icons/ directory.
        if icons_dir.is_dir():
            for icon_path in icons_dir.glob("*.png"):
                route_key = icon_path.stem.replace("_black", "").strip().upper()
                if not route_key or route_key in self.route_icon_cache:
                    continue
                try:
                    image = Image.open(icon_path).convert('RGB')
                    image = image.resize(Config.Layout.ICON_SIZE, resample_mode)
                    self.route_icon_cache[route_key] = image
                except Exception:
                    continue

        # Ensure explicitly configured icons are also attempted.
        icon_map = getattr(Config.Files, "ROUTE_ICONS", {})
        for route_key, raw_path in icon_map.items():
            normalized_route = str(route_key).strip().upper()
            if not normalized_route or normalized_route in self.route_icon_cache:
                continue
            try:
                resolved = self._resolve_asset_path(raw_path)
                image = Image.open(resolved).convert('RGB')
                image = image.resize(Config.Layout.ICON_SIZE, resample_mode)
                self.route_icon_cache[normalized_route] = image
            except Exception:
                continue

    def _display_line_logo(self, route: str, position: Tuple[int, int]) -> bool:
        """Load and display route icon at specified position"""
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
                image = Image.open(icon_path)
                image = image.resize(Config.Layout.ICON_SIZE, resample_mode)
                image = image.convert('RGB')
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
            self._station_scroll_index = (self._station_scroll_index + steps) % len(cycle_text)
            self._station_scroll_last_update += steps * scroll_step

        rolling_text = cycle_text + cycle_text
        return rolling_text[self._station_scroll_index : self._station_scroll_index + visible_chars]
    
    def _format_single_time(self, time_str: str) -> str:
        """Format a single arrival time to fit in 3 characters"""
        if not time_str or time_str == 'No data':
            return '---'
        
        # Convert "2 min" → "2m", "Now" → "NOW"
        formatted = time_str.replace(' min', 'm').replace('Now', 'NOW')
        
        # If longer than 3 chars (e.g., "127m"), remove the 'm'
        if len(formatted) > Config.Display.TIME_MAX_CHARS:
            formatted = formatted.replace('m', '')[:Config.Display.TIME_MAX_CHARS]
        
        return formatted
    
    def _draw_text(self, text: str, position: Tuple[int, int], color: Tuple[int, int, int]):
        """Draw text at specified position with color"""
        if self.font:
            graphics.DrawText(self.canvas, self.font, position[0], position[1], 
                            graphics.Color(*color), text)
    
    def get_realtime_data(
        self,
        routes: Sequence[str],
        station_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], List[str], List[str]]:
        """Fetch real-time MTA data for preferred routes"""
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
            
            if data.get('status') != 'success':
                print("✗ Train API returned error status")
                return None, [], []
            
            trains = data.get('trains', {})
            fallback_route = None
            fallback_times = ([], [])
            
            for route in routes_to_check:
                if route not in trains:
                    continue
                
                route_data = trains[route]
                uptown = route_data.get('uptown', {}).get('next_arrivals', [])
                downtown = route_data.get('downtown', {}).get('next_arrivals', [])
                
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
    
    def _draw_station_info(self, route: str, station_name_window: Optional[str] = None):
        """Draw station information: line logo + station name"""
        # Clear header regions so station/route updates do not leave stale pixels.
        self.clear_area(Config.Layout.ICON_POSITION, Config.Layout.ICON_SIZE)
        station_clear_width = Config.Display.STATION_NAME_VISIBLE_CHARS * Config.Layout.CHAR_WIDTH
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

        # Line logo (e.g., F train icon). If no asset exists, draw route text.
        if not self._display_line_logo(route, Config.Layout.ICON_POSITION):
            print(f"⚠️ Icon unavailable for route {route}; using text fallback")
            self._draw_route_fallback(route)

        # Station name (scrolling window for long names)
        if station_name_window is None:
            station_name_window = self._get_station_name_window()
        self._draw_text(
            station_name_window,
            Config.Layout.STATION_NAME_POSITION,
            Config.Colors.WHITE,
        )
    
    def clear_area(self, position: Tuple[int, int], size: Tuple[int, int]):
        """Clear an area of the canvas"""
        for col in range(position[0], position[0] + size[0]):
            for row in range(position[1], position[1] + size[1]):
                if 0 <= col < Config.Hardware.COLS and 0 <= row < Config.Hardware.ROWS:
                    self.canvas.SetPixel(col, row, 0, 0, 0)
    
    def _draw_direction_label(self, direction_name: str, label_position: Tuple[int, int]):
        """Draw direction label (static)"""
        self._draw_text(direction_name, label_position, Config.Colors.WHITE)
    
    def _draw_time_box(self, time_str: str, position: Tuple[int, int], color: Tuple[int, int, int]):
        """Draw a single arrival time in its box (clear + draw)"""
        # Clear the box first
        self.clear_area([position[0], position[1] - Config.Layout.CHAR_HEIGHT], [Config.Layout.TIME_BOX_WIDTH, Config.Layout.TIME_BOX_HEIGHT])
        
        # Format and draw the time
        formatted_time = self._format_single_time(time_str)
        self._draw_text(formatted_time, position, color)
    
    def show_arrival_times(self, times: List[str], box_positions: List[Tuple[int, int]], color: Tuple[int, int, int]):
        """Draw all arrival times for one direction (updates 3 boxes)"""
        # Ensure we have exactly 3 times (pad with empty if needed)
        padded_times = (times + [''] * Config.Display.ARRIVALS_PER_DIRECTION)[:Config.Display.ARRIVALS_PER_DIRECTION]
        
        # Draw each time in its own box
        for time_str, position in zip(padded_times, box_positions):
            self._draw_time_box(time_str, position, color)

    def _draw_bike(self, position: Tuple[int, int], color: Tuple[int, int, int]):
        """Draw a 6x10 bike """
        x, y = position
        
        icon_pattern = [
            [0, 1, 1, 1, 0, 0, 0, 0, 0, 0],  
            [0, 0, 1, 0, 1, 1, 0, 0, 0, 0], 
            [0, 1, 1, 0, 0, 1, 0, 1, 1, 0], 
            [1, 0, 0, 1, 1, 1, 1, 0, 0, 1], 
            [1, 0, 0, 1, 0, 0, 1, 0, 0, 1], 
            [0, 1, 1, 0, 0, 0, 0, 1, 1, 0]   
        ]
        
        for row in range(len(icon_pattern)):
            for col in range(len(icon_pattern[row])):
                if icon_pattern[row][col] == 1:
                    self.canvas.SetPixel(x + col, y + row, color[0], color[1], color[2])

    def _draw_ebike(self, position: Tuple[int, int], color: Tuple[int, int, int]):
        """Draw a plug indicator"""
        x, y = position
        
        icon_pattern = [
            [0, 0, 1, 0],
            [0, 1, 0, 0], 
            [1, 1, 1, 1],  
            [0, 0, 1, 0],  
            [0, 1, 0, 0],  
            [1, 0, 0, 0]   
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
        """Show MTA station info"""

        self._draw_station_info(route, station_name_window=station_name_window)
        self._draw_direction_label(directions[0], Config.Layout.UPTOWN_LABEL_POSITION)
        self._draw_direction_label(directions[1], Config.Layout.DOWNTOWN_LABEL_POSITION)
    
    def show_mta_arrival_times(self, route: str, uptown_times: List[str], downtown_times: List[str]):
        """Display complete MTA board with all components"""
        
        # Dynamic: Update only arrival times (every refresh) - 6 individual boxes
        uptown_positions = [
            Config.Layout.UPTOWN_TIME_1_POSITION,
            Config.Layout.UPTOWN_TIME_2_POSITION,
            Config.Layout.UPTOWN_TIME_3_POSITION
        ]
        downtown_positions = [
            Config.Layout.DOWNTOWN_TIME_1_POSITION,
            Config.Layout.DOWNTOWN_TIME_2_POSITION,
            Config.Layout.DOWNTOWN_TIME_3_POSITION
        ]
        
        self.show_arrival_times(uptown_times, uptown_positions, Config.Colors.GREEN)
        self.show_arrival_times(downtown_times, downtown_positions, Config.Colors.YELLOW)
        
        # Update display
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        
    def draw_citibike_icons(self):
        """Draw Citi Bike icons (not shown by default)"""
        self._draw_bike(Config.Layout.BIKE_ICON_POSITION, Config.Colors.DAZZLING_BLUE)
        self._draw_ebike(Config.Layout.EBIKE_ICON_POSITION, Config.Colors.DAZZLING_BLUE)

    def show_citibike_status(self, data: Dict):
        """Show Cibike status"""
        num_normal_bikes = max(0, data.get('num_bikes_available', 0) - data.get('num_ebikes_available', 0))
        num_ebikes = max(0, data.get('num_ebikes_available', 0))

        bike_time_position = [Config.Layout.BIKE_ICON_POSITION[0] + 11, Config.Layout.BIKE_ICON_POSITION[1] + 6]
        ebike_time_position = [Config.Layout.EBIKE_ICON_POSITION[0] + 5, Config.Layout.EBIKE_ICON_POSITION[1] + 6]

        self.clear_area([bike_time_position[0], bike_time_position[1] - 6], [Config.Layout.CHAR_WIDTH * 2, Config.Layout.CHAR_HEIGHT])
        self.clear_area([ebike_time_position[0], ebike_time_position[1] - 6], [Config.Layout.CHAR_WIDTH * 2, Config.Layout.CHAR_HEIGHT])
        self._draw_text(f"{num_normal_bikes}", bike_time_position,  Config.Colors.BLUE if num_normal_bikes > 0 else Config.Colors.RED)
        self._draw_text(f"{num_ebikes}", ebike_time_position, Config.Colors.BLUE if num_ebikes > 0 else Config.Colors.RED)
    
    def clear(self):
        """Clear the display"""
        self.canvas.Clear()
        self.canvas = self.matrix.SwapOnVSync(self.canvas)


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


def build_display_schedule(station_ids: List[str]) -> DisplaySchedule:
    """Build station/line rotation schedule from configured stations."""

    def _line_lookup(station_id: str) -> List[str]:
        if not is_valid_station(station_id):
            print(f"⚠️ Skipping invalid station in schedule: {station_id}")
            return []

        merged: List[str] = []
        seen: set[str] = set()
        for route in get_station_lines(station_id):
            route = str(route).strip().upper()
            if not route or route in seen:
                continue
            seen.add(route)
            merged.append(route)
        return merged

    fallback_route = Config.MTA.ROUTES[0] if Config.MTA.ROUTES else "F"
    if is_valid_station(Config.MTA.STATION):
        fallback_lines = _line_lookup(Config.MTA.STATION)
        if fallback_lines:
            fallback_route = fallback_lines[0]

    valid_station_ids = [station_id for station_id in station_ids if is_valid_station(station_id)]
    if not valid_station_ids:
        valid_station_ids = [Config.MTA.STATION]

    schedule = create_display_schedule(
        station_ids=valid_station_ids,
        line_lookup=_line_lookup,
        interval_seconds=Config.Display.ROTATION_INTERVAL,
        default_view=DisplayView(
            station_id=Config.MTA.STATION,
            route_id=fallback_route,
        ),
    )
    schedule_label = ", ".join(
        f"{view.station_id}:{view.route_id}" for view in schedule.views
    )
    print(
        f"📋 Display schedule ({schedule.interval_seconds}s): "
        f"{schedule_label if schedule_label else '[empty]'}"
    )
    return schedule


def get_available_view_index(
    schedule: DisplaySchedule,
    start_index: int,
    unavailable_until: Dict[CacheKey, int],
    now_ts: int,
) -> Optional[int]:
    """Get next available schedule index, skipping unavailable routes."""
    if not schedule.views:
        return None

    normalized_start = start_index % len(schedule.views)

    for offset in range(len(schedule.views)):
        idx = (normalized_start + offset) % len(schedule.views)
        candidate = schedule.views[idx]
        key = (candidate.station_id, candidate.route_id)
        if unavailable_until.get(key, 0) <= now_ts:
            return idx

    return None


def should_run_interval(last_run_ts: int, now_ts: int, interval_seconds: int) -> bool:
    """Return True when interval has elapsed."""
    return (now_ts - last_run_ts) >= interval_seconds


def is_cache_stale(
    cached_arrivals: Optional[ArrivalCacheValue], now_ts: int
) -> bool:
    """Return True when cached arrivals need refresh."""
    return (
        cached_arrivals is None
        or (now_ts - cached_arrivals[0]) >= Config.Display.REFRESH_INTERVAL
    )


def get_station_feed_data(
    display: MTALEDDisplay,
    station_feed_cache: Dict[str, StationFeedCacheValue],
) -> Optional[Dict[str, Any]]:
    """Return the latest cached station feed snapshot for the station."""
    cached_station_feed = station_feed_cache.get(display.station_id)
    if cached_station_feed is None:
        return None
    return cached_station_feed[1]


def _schedule_station_ids(schedule: DisplaySchedule) -> List[str]:
    station_ids: List[str] = []
    seen: set[str] = set()
    for view in schedule.views:
        if view.station_id in seen:
            continue
        seen.add(view.station_id)
        station_ids.append(view.station_id)
    return station_ids


def _preferred_routes_by_station(schedule: DisplaySchedule) -> Dict[str, List[str]]:
    routes_by_station: Dict[str, List[str]] = {}
    for view in schedule.views:
        routes = routes_by_station.setdefault(view.station_id, [])
        if view.route_id not in routes:
            routes.append(view.route_id)
    return routes_by_station


def maybe_refresh_station_feeds(state: RuntimeState, now_ts: int):
    """Refresh all configured station feeds once per refresh interval."""
    if not should_run_interval(
        state.last_station_feed_refresh_ts,
        now_ts,
        Config.Display.REFRESH_INTERVAL,
    ):
        return

    station_ids = _schedule_station_ids(state.schedule)
    if not station_ids:
        state.last_station_feed_refresh_ts = now_ts
        return

    preferred_routes = _preferred_routes_by_station(state.schedule)
    station_labels = ", ".join(
        f"{get_station_name(station_id)} ({station_id})" for station_id in station_ids
    )
    print(f"🔄 Refreshing station feeds: {station_labels}")

    station_payloads = get_train_status_batch(
        station_ids,
        preferred_routes_by_station=preferred_routes,
    )

    state.station_feed_cache.clear()
    for station_id in station_ids:
        station_payload = station_payloads.get(station_id)
        if station_payload is None:
            continue
        state.station_feed_cache[station_id] = (now_ts, station_payload)

    state.last_station_feed_refresh_ts = now_ts
    state.arrival_cache.clear()
    state.unavailable_until.clear()


def refresh_view_arrivals(
    display: MTALEDDisplay,
    current_route: str,
    now_ts: int,
    arrival_cache: Dict[CacheKey, ArrivalCacheValue],
    station_feed_cache: Dict[str, StationFeedCacheValue],
    unavailable_until: Dict[CacheKey, int],
) -> Tuple[List[str], List[str], bool]:
    """Refresh arrivals for active view; return times and availability."""
    station_data = get_station_feed_data(display, station_feed_cache)
    if station_data is None:
        print(
            f"⚠️ No station feed snapshot available for "
            f"{get_station_name(display.station_id)}"
        )
        route, uptown, downtown = None, [], []
    else:
        route, uptown, downtown = display.get_realtime_data(
            [current_route],
            station_data=station_data,
        )
    if not route:
        uptown, downtown = [], []

    cache_key = (display.station_id, current_route)
    if not uptown and not downtown:
        unavailable_until[cache_key] = now_ts + Config.Display.REFRESH_INTERVAL
        arrival_cache.pop(cache_key, None)
        print(
            f"⚠️ Skipping unavailable view {cache_key[0]}:{cache_key[1]} "
            f"for {Config.Display.REFRESH_INTERVAL}s"
        )
        return uptown, downtown, False

    arrival_cache[cache_key] = (now_ts, uptown, downtown)
    unavailable_until.pop(cache_key, None)
    return uptown, downtown, True


def reload_runtime_config(
    config_path: Path,
    schedule: DisplaySchedule,
    active_index: int,
    now_ts: int,
    arrival_cache: Dict[CacheKey, ArrivalCacheValue],
    station_feed_cache: Dict[str, StationFeedCacheValue],
    unavailable_until: Dict[CacheKey, int],
) -> Tuple[DisplaySchedule, int, bool]:
    """Reload config and schedule from board.json."""
    previous_refresh = Config.Display.REFRESH_INTERVAL
    previous_rotation = Config.Display.ROTATION_INTERVAL
    previous_citibike = Config.CitiBike.STATION_ID

    try:
        board_config = load_board_config(config_path)
        apply_board_config(board_config)
        reloaded_schedule = build_display_schedule(board_config.stations)
    except Exception as exc:
        print(f"⚠️ Config reload failed: {exc}")
        return schedule, active_index, False

    if not reloaded_schedule.views:
        print("⚠️ Config reload ignored: empty schedule.")
        return schedule, active_index, False

    schedule_changed = reloaded_schedule != schedule
    settings_changed = (
        previous_refresh != Config.Display.REFRESH_INTERVAL
        or previous_rotation != Config.Display.ROTATION_INTERVAL
        or previous_citibike != Config.CitiBike.STATION_ID
    )
    if not schedule_changed and not settings_changed:
        return schedule, active_index, False

    arrival_cache.clear()
    station_feed_cache.clear()
    unavailable_until.clear()

    next_index = get_available_view_index(
        schedule=reloaded_schedule,
        start_index=active_index,
        unavailable_until=unavailable_until,
        now_ts=now_ts,
    )
    if next_index is None:
        next_index = 0

    print(f"♻️ Reloaded board config from {config_path}")
    return reloaded_schedule, next_index, True


def maybe_reload_board_config(
    config_path: Path,
    state: RuntimeState,
    now: float,
    now_ts: int,
):
    """Apply board.json changes on refresh cadence."""
    if not should_run_interval(
        state.last_config_reload_check_ts,
        now_ts,
        Config.Display.REFRESH_INTERVAL,
    ):
        return

    reloaded_schedule, reloaded_index, config_reloaded = reload_runtime_config(
        config_path=config_path,
        schedule=state.schedule,
        active_index=state.active_index,
        now_ts=now_ts,
        arrival_cache=state.arrival_cache,
        station_feed_cache=state.station_feed_cache,
        unavailable_until=state.unavailable_until,
    )
    state.last_config_reload_check_ts = now_ts

    if not config_reloaded:
        return

    state.schedule = reloaded_schedule
    state.active_index = reloaded_index
    state.next_rotation_ts = now + state.schedule.interval_seconds
    state.last_render_signature = None
    state.last_station_feed_refresh_ts = 0


def maybe_rotate_display_view(state: RuntimeState, now: float, now_ts: int):
    """Advance to next available station/line view on rotation cadence."""
    if now < state.next_rotation_ts:
        return

    next_index = get_available_view_index(
        schedule=state.schedule,
        start_index=state.active_index + 1,
        unavailable_until=state.unavailable_until,
        now_ts=now_ts,
    )
    if next_index is not None:
        state.active_index = next_index

    state.next_rotation_ts = now + state.schedule.interval_seconds


def sync_display_view(display: MTALEDDisplay, state: RuntimeState):
    """Ensure display object tracks active schedule view."""
    active_view = state.schedule.views[state.active_index]
    if display.station_id != active_view.station_id:
        display.set_station(active_view.station_id)

    if state.current_route != active_view.route_id:
        state.current_route = active_view.route_id
        print(f"🔁 Switching line to {state.current_route}")


def get_arrivals_for_active_view(
    display: MTALEDDisplay,
    state: RuntimeState,
    now: float,
    now_ts: int,
) -> Optional[Tuple[List[str], List[str]]]:
    """Return arrivals for active view or None when view should be skipped."""
    cache_key = (display.station_id, state.current_route)
    cached_arrivals = state.arrival_cache.get(cache_key)
    if is_cache_stale(cached_arrivals, now_ts):
        uptown, downtown, has_arrivals = refresh_view_arrivals(
            display=display,
            current_route=state.current_route,
            now_ts=now_ts,
            arrival_cache=state.arrival_cache,
            station_feed_cache=state.station_feed_cache,
            unavailable_until=state.unavailable_until,
        )
        if not has_arrivals:
            next_index = get_available_view_index(
                schedule=state.schedule,
                start_index=state.active_index + 1,
                unavailable_until=state.unavailable_until,
                now_ts=now_ts,
            )
            if next_index is not None and next_index != state.active_index:
                state.active_index = next_index
                state.next_rotation_ts = now + state.schedule.interval_seconds
            return None
        return uptown, downtown

    assert cached_arrivals is not None
    _, uptown, downtown = cached_arrivals
    return uptown, downtown


def maybe_render_view(
    display: MTALEDDisplay,
    state: RuntimeState,
    uptown: List[str],
    downtown: List[str],
):
    """Render view only when content changes."""
    station_name_window = display._get_station_name_window()
    render_signature = (
        display.station_id,
        state.current_route,
        tuple(uptown),
        tuple(downtown),
        station_name_window,
    )
    if render_signature == state.last_render_signature:
        return

    display.show_mta_station_info(
        state.current_route,
        DIRECTION_LABELS,
        station_name_window=station_name_window,
    )
    display.show_mta_arrival_times(state.current_route, uptown, downtown)
    state.last_render_signature = render_signature


def maybe_refresh_citibike(now_ts: int, state: RuntimeState):
    """Refresh Citi Bike data on refresh cadence."""
    if not Config.CitiBike.ENABLED:
        return

    if not should_run_interval(
        state.last_citibike_fetch_ts,
        now_ts,
        Config.Display.REFRESH_INTERVAL,
    ):
        return

    try:
        get_station_data(Config.CitiBike.STATION_ID)
    except Exception as exc:
        print(f"Error getting citibike data: {exc}")
    state.last_citibike_fetch_ts = now_ts


def main():
    """Run real-time MTA display"""
    config_path = resolve_board_config_path()
    board_config = load_board_config(config_path)
    apply_board_config(board_config)
    schedule = build_display_schedule(board_config.stations)
    if not schedule.views:
        print("✗ No display views available. Exiting.")
        return

    initial_index = get_available_view_index(
        schedule=schedule,
        start_index=0,
        unavailable_until={},
        now_ts=int(time.time()),
    )
    if initial_index is None:
        print("✗ No available display views. Exiting.")
        return
    active_view = schedule.views[initial_index]

    print(
        f"🚇 Starting MTA display scheduler @ {schedule.interval_seconds}s "
        f"rotation, {Config.Display.REFRESH_INTERVAL}s refresh"
    )
    display = MTALEDDisplay(active_view.station_id)
    start_ts = time.time()
    state = RuntimeState(
        schedule=schedule,
        active_index=initial_index,
        current_route=active_view.route_id,
        next_rotation_ts=start_ts + schedule.interval_seconds,
        last_config_reload_check_ts=int(start_ts),
    )

    print(
        f"🧩 Hot reload enabled for {config_path} "
        f"(every {Config.Display.REFRESH_INTERVAL}s refresh)"
    )
    
    try:
        display.clear()

        while True:
            now = time.time()
            now_ts = int(now)

            maybe_reload_board_config(config_path, state, now, now_ts)
            maybe_refresh_station_feeds(state, now_ts)
            maybe_rotate_display_view(state, now, now_ts)
            sync_display_view(display, state)

            arrivals = get_arrivals_for_active_view(display, state, now, now_ts)
            if arrivals is None:
                time.sleep(Config.Display.UI_TICK_INTERVAL)
                continue
            uptown, downtown = arrivals

            maybe_render_view(display, state, uptown, downtown)
            maybe_refresh_citibike(now_ts, state)

            time.sleep(max(0.2, Config.Display.UI_TICK_INTERVAL))
            
    except KeyboardInterrupt:
        display.clear()
        print(f"\n🛑 Display stopped.")


if __name__ == "__main__":
    main()
