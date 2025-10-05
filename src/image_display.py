#!/usr/bin/env python3
"""
Real-time MTA LED Display using PNG images for route icons
Fetches live MTA data and displays on 64x32 LED matrix with 30-second refresh
"""

import sys
import time
from typing import Tuple, List, Optional

sys.path.append('/home/hung/rpi-rgb-led-matrix/bindings/python')

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from PIL import Image

# Import MTA data functions
from app import get_train_status
from station_data import is_valid_station, get_station_name

# Configuration Constants
class Config:
    """Organized configuration for MTA LED Display"""
    
    class Hardware:
        """LED matrix hardware settings"""
        ROWS = 32
        COLS = 64
        BRIGHTNESS = 20
        MAPPING = 'adafruit-hat'
        GPIO_SLOWDOWN = 5
    
    class Files:
        """File paths for fonts and icons"""
        FONT = '../fonts/4x6.bdf'
        ROUTE_ICON = '../icons/F_black.png'
    
    class Layout:
        """Display layout positions and sizes"""
        ICON_SIZE = (18, 18)
        ICON_POSITION = (1, 7)
        
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
    
    class Colors:
        """RGB color definitions"""
        WHITE = (255, 255, 255)
        GREEN = (0, 255, 0)
        YELLOW = (255, 255, 0)
    
    class Display:
        """Display behavior settings"""
        ARRIVALS_PER_DIRECTION = 3  # Show 3 arrival times per direction
        STATION_NAME_MAX_LENGTH = 5
        REFRESH_INTERVAL = 30
        TIME_MAX_CHARS = 3  # Max characters per time box
    
    class MTA:
        """MTA station and route defaults"""
        STATION = "B10"  # 57th St F train
        ROUTE = "F"


class MTALEDDisplay:
    """Real-time MTA LED display with route icons"""
    
    def __init__(self, station_id: str = Config.MTA.STATION):
        self.station_id = self._validate_station(station_id)
        self.static_drawn = False  # Track if static elements are drawn
        
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
    
    def _display_line_logo(self, position: Tuple[int, int]) -> bool:
        """Load and display route icon at specified position"""
        try:
            image = Image.open(Config.Files.ROUTE_ICON)
            image = image.resize(Config.Layout.ICON_SIZE, Image.Resampling.LANCZOS)
            image = image.convert('RGB')
            self.canvas.SetImage(image, position[0], position[1])
            return True
        except Exception as e:
            print(f"✗ Error displaying route icon: {e}")
            return False
    
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
    
    def get_realtime_data(self, route: str) -> Tuple[List[str], List[str]]:
        """Fetch real-time MTA data for specified route"""
        try:
            print(f"🔄 Fetching {route} train data for {get_station_name(self.station_id)}...")
            data = get_train_status(self.station_id)
            
            if data.get('status') != 'success' or route not in data.get('trains', {}):
                print(f"✗ No {route} train data available")
                return [], []
            
            route_data = data['trains'][route]
            uptown = route_data.get('uptown', {}).get('next_arrivals', [])
            downtown = route_data.get('downtown', {}).get('next_arrivals', [])
            
            print(f"✓ Uptown: {uptown} | Downtown: {downtown}")
            return uptown, downtown
                
        except Exception as e:
            print(f"✗ Error: {e}")
            return [], []
    
    def _draw_station_info(self, route: str):
        """Draw station information: line logo + station name"""
        # Line logo (e.g., F train icon)
        self._display_line_logo(Config.Layout.ICON_POSITION)
        
        # Station name (e.g., "57th St")
        station_name = get_station_name(self.station_id)[:Config.Display.STATION_NAME_MAX_LENGTH]
        print(f"Station name: {station_name}")
        self._draw_text(station_name, Config.Layout.STATION_NAME_POSITION, Config.Colors.WHITE)
    
    def _clear_time_box(self, position: Tuple[int, int]):
        """Clear a single time box (12x6 pixels for 3 characters)"""
        x, y = position
        # BDF fonts: y is baseline, text appears ABOVE it
        # For 4x6 font: FONT_ASCENT = 5, FONT_DESCENT = 1
        # Clear from (y - 5) to (y + 1) = 6 pixels total
        y_start = y - 5  # Start 5 pixels above baseline
        
        for dy in range(Config.Layout.TIME_BOX_HEIGHT):
            for dx in range(Config.Layout.TIME_BOX_WIDTH):
                if x + dx < Config.Hardware.COLS and y_start + dy >= 0 and y_start + dy < Config.Hardware.ROWS:
                    self.canvas.SetPixel(x + dx, y_start + dy, 0, 0, 0)
    
    def _draw_direction_label(self, direction_name: str, label_position: Tuple[int, int]):
        """Draw direction label (static - drawn once)"""
        self._draw_text(direction_name, label_position, Config.Colors.WHITE)
    
    def _draw_time_box(self, time_str: str, position: Tuple[int, int], color: Tuple[int, int, int]):
        """Draw a single arrival time in its box (clear + draw)"""
        # Clear the box first
        self._clear_time_box(position)
        
        # Format and draw the time
        formatted_time = self._format_single_time(time_str)
        self._draw_text(formatted_time, position, color)
    
    def _draw_direction_times(self, times: List[str], box_positions: List[Tuple[int, int]], 
                             color: Tuple[int, int, int]):
        """Draw all arrival times for one direction (updates 3 boxes)"""
        # Ensure we have exactly 3 times (pad with empty if needed)
        padded_times = (times + [''] * Config.Display.ARRIVALS_PER_DIRECTION)[:Config.Display.ARRIVALS_PER_DIRECTION]
        
        # Draw each time in its own box
        for time_str, position in zip(padded_times, box_positions):
            self._draw_time_box(time_str, position, color)
    
    def display_route(self, route: str, uptown_times: List[str], downtown_times: List[str]):
        """Display complete MTA board with all components"""
        if not self.font:
            print("✗ No font available, cannot display")
            return
        
        # Draw static elements only on first call
        if not self.static_drawn:
            self.canvas.Clear()
            
            # Static: Station Info (line logo + station name)
            self._draw_station_info(route)
            
            # Static: Direction labels
            self._draw_direction_label('UPTOWN', Config.Layout.UPTOWN_LABEL_POSITION)
            self._draw_direction_label('DOWNTOWN', Config.Layout.DOWNTOWN_LABEL_POSITION)
            
            self.static_drawn = True
            print("✓ Static elements drawn")
        
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
        
        self._draw_direction_times(uptown_times, uptown_positions, Config.Colors.GREEN)
        self._draw_direction_times(downtown_times, downtown_positions, Config.Colors.YELLOW)
        
        # Update display
        self.matrix.SwapOnVSync(self.canvas)
    
    def clear(self):
        """Clear the display"""
        self.canvas.Clear()
        self.static_drawn = False  # Reset flag
        self.matrix.SwapOnVSync(self.canvas)


def main():
    """Run real-time MTA display"""
    print(f"🚇 Starting MTA display: {Config.MTA.ROUTE} train @ {get_station_name(Config.MTA.STATION)}")
    display = MTALEDDisplay(Config.MTA.STATION)
    
    try:
        while True:
            # Fetch fresh data
            uptown, downtown = display.get_realtime_data(Config.MTA.ROUTE)
            
            # Use fallback if no data
            if not uptown and not downtown:
                print("⚠️ Using fallback data (no real data available)")
                uptown, downtown = ['No', 'Data'], ['Check', 'API']
            
            # Update display
            display.display_route(Config.MTA.ROUTE, uptown, downtown)
            
            # Wait for next update
            print(f"⏰ Next update in {Config.Display.REFRESH_INTERVAL} seconds... (Ctrl+C to stop)")
            time.sleep(Config.Display.REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        display.clear()
        print(f"\n🛑 Display stopped.")
    except Exception as e:
        display.clear()
        print(f"\n❌ Display error: {e}")


if __name__ == "__main__":
    main()