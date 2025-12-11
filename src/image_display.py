#!/usr/bin/env python3
"""
Real-time MTA LED Display using PNG images for route icons
Fetches live MTA data and displays on 64x32 LED matrix with 30-second refresh
"""

import sys
import time
from typing import Tuple, List, Optional, Dict

sys.path.append('/home/hung/rpi-rgb-led-matrix/bindings/python')

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from PIL import Image
from datetime import datetime
# Import Citi Bike data functions
import sys
sys.path.append('../citibike')
from citibike import get_station_data, get_station_info

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
        BRIGHTNESS = 10
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
        STATION_NAME_MAX_LENGTH = 5
        REFRESH_INTERVAL = 30
        TIME_MAX_CHARS = 3  # Max characters per time box
    
    class MTA:
        """MTA station and route defaults"""
        STATION = "B10"  # 57th St F train
        ROUTE = "F"

    class CitiBike:
        """Citi Bike station and route defaults"""
        STATION_ID = "66dbc551-0aca-11e7-82f6-3863bb44ef7c"


class MTALEDDisplay:
    """Real-time MTA LED display with route icons"""
    
    def __init__(self, station_id: str = Config.MTA.STATION):
        self.station_id = self._validate_station(station_id)
        
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
    
    def clear_area(self, position: Tuple[int, int], size: Tuple[int, int]):
        """Clear an area of the canvas"""
        for col in range(position[0], position[0] + size[0]):
            for row in range(position[1], position[1] + size[1]):
                if col < Config.Hardware.COLS and row < Config.Hardware.ROWS:
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
            [0, 1, 0, 1, 0],
            [0, 1, 0, 1, 0], 
            [1, 1, 1, 1, 1],  
            [0, 0, 1, 0, 0],  
            [1, 0, 1, 0, 0],  
            [1, 1, 1, 0, 0]   
        ]

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

    def show_mta_station_info(self, route: str, directions: List[str]):
        """Show MTA station info"""

        self._draw_station_info(route)
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
        self.matrix.SwapOnVSync(self.canvas)
        
    def show_citibike_station_info(self):
        """Show Cibike station info"""
        self._draw_bike(Config.Layout.BIKE_ICON_POSITION, Config.Colors.DAZZLING_BLUE)
        self._draw_ebike(Config.Layout.EBIKE_ICON_POSITION, Config.Colors.DAZZLING_BLUE)

    def show_citibike_status(self, data: Dict):
        """Show Cibike status"""
        num_normal_bikes = data['num_bikes_available'] - data['num_ebikes_available']
        num_ebikes = data['num_ebikes_available']

        bike_time_position = [Config.Layout.BIKE_ICON_POSITION[0] + 11, Config.Layout.BIKE_ICON_POSITION[1] + 6]
        ebike_time_position = [Config.Layout.EBIKE_ICON_POSITION[0] + 5, Config.Layout.EBIKE_ICON_POSITION[1] + 6]

        self.clear_area([bike_time_position[0], bike_time_position[1] - 6], [Config.Layout.CHAR_WIDTH * 2, Config.Layout.CHAR_HEIGHT])
        self.clear_area([ebike_time_position[0], ebike_time_position[1] - 6], [Config.Layout.CHAR_WIDTH * 2, Config.Layout.CHAR_HEIGHT])
        self._draw_text(f"{num_normal_bikes}", bike_time_position,  Config.Colors.BLUE if num_normal_bikes > 0 else Config.Colors.RED)
        self._draw_text(f"{num_ebikes}", ebike_time_position, Config.Colors.BLUE if num_ebikes > 0 else Config.Colors.RED)
    
    def clear(self):
        """Clear the display"""
        self.canvas.Clear()
        self.matrix.SwapOnVSync(self.canvas)


def main():
    """Run real-time MTA display"""
    print(f"🚇 Starting MTA display: {Config.MTA.ROUTE} train @ {get_station_name(Config.MTA.STATION)}")
    display = MTALEDDisplay(Config.MTA.STATION)
    
    try:
        display.clear()
        display.show_mta_station_info(Config.MTA.ROUTE, ['UPTOWN', 'DOWNTOWN'])
        display.show_citibike_station_info()
        station_info = get_station_info("W 56 St & 6 Ave")
        print(f"Station Info: {station_info}")

        while True:
            try:
                citibike_data = get_station_data(station_info['station_id'])
            except Exception as e:
                print(f"Error getting citibike data: {e}")
                citibike_data = {
                    'num_bikes_available': 0,
                    'num_ebikes_available': 0
                }

            uptown, downtown = display.get_realtime_data(Config.MTA.ROUTE)
            
            # Use fallback if no data
            if not uptown and not downtown:
                print("⚠️ Using fallback data (no real data available)")
                uptown, downtown = ['No', 'Data'], ['Check', 'API']
            
            # Update display
            display.show_mta_arrival_times(Config.MTA.ROUTE, uptown, downtown)
            display.show_citibike_status(citibike_data)
            
            # Wait for next update
            print(f"⏰ Next update in {Config.Display.REFRESH_INTERVAL} seconds... (Ctrl+C to stop)")
            time.sleep(Config.Display.REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        display.clear()
        print(f"\n🛑 Display stopped.")


if __name__ == "__main__":
    main()