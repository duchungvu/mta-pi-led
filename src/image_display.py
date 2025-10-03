#!/usr/bin/env python3
"""
Real-time MTA LED Display using PNG images for route icons
Fetches live MTA data and displays on 64x64 LED matrix with 30-second refresh
"""

import sys
import time
import os
from typing import Tuple, List, Optional
from datetime import datetime

sys.path.append('/home/hung/rpi-rgb-led-matrix/bindings/python')

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from PIL import Image

# Import MTA data functions
from app import get_train_status
from station_data import is_valid_station, get_station_name

# Configuration Constants
class Config:
    # Display settings
    MATRIX_ROWS = 32
    MATRIX_COLS = 64
    MATRIX_BRIGHTNESS = 25
    HARDWARE_MAPPING = 'adafruit-hat'
    GPIO_SLOWDOWN = 5
    
    # File paths
    FONT_PATH = '../fonts/tom-thumb.bdf'
    ICONS_DIR = '../icons'
    
    # Display layout
    ICON_SIZE = (18, 18)
    FIRST_ICON_POSITION = (1, 7)
    SECOND_ICON_POSITION = (1, 17)
    
    STATION_NAME_POSITION = (1, 6)
    UPDATE_TIME_POSITION = (1, 32)
    UPTOWN_LABEL_POSITION = (24, 6)
    UPTOWN_TIMES_POSITION = (24, 11)
    DOWNTOWN_LABEL_POSITION = (24, 18)  # Moved up from 20
    DOWNTOWN_TIMES_POSITION = (24, 23)  # Moved up from 26
    
    # Colors (RGB tuples)
    WHITE = (255, 255, 255)
    GREEN = (0, 255, 0)
    YELLOW = (255, 255, 0)
    ORANGE = (255, 99, 25)
    GRAY = (100, 100, 100)
    
    # Display settings
    MAX_ARRIVALS = 3
    STATION_NAME_MAX_LENGTH = 5
    REFRESH_INTERVAL = 30
    
    # Default station and route
    DEFAULT_STATION = "B10"  # 57th St F train
    DEFAULT_ROUTE = "F"
    
    # Supported image extensions
    IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']


class MTALEDDisplay:
    """Real-time MTA LED display with route icons"""
    
    def __init__(self, station_id: str = Config.DEFAULT_STATION):
        self.station_id = self._validate_station(station_id)
        self.last_update: Optional[str] = None
        
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
        return Config.DEFAULT_STATION
    
    def _setup_matrix(self) -> RGBMatrix:
        """Configure and initialize LED matrix"""
        options = RGBMatrixOptions()
        options.rows = Config.MATRIX_ROWS
        options.cols = Config.MATRIX_COLS
        options.hardware_mapping = Config.HARDWARE_MAPPING
        options.gpio_slowdown = Config.GPIO_SLOWDOWN
        options.brightness = Config.MATRIX_BRIGHTNESS
        
        matrix = RGBMatrix(options=options)
        print("✓ LED matrix initialized")
        return matrix
    
    def _load_font(self) -> Optional[graphics.Font]:
        """Load display font"""
        try:
            font = graphics.Font()
            font.LoadFont(Config.FONT_PATH)
            print("✓ Font loaded")
            return font
        except Exception as e:
            print(f"✗ Font loading failed: {e}")
            return None
    
    def _find_route_icon(self, route: str) -> Optional[str]:
        """Find icon file for given route"""
        if not os.path.exists(Config.ICONS_DIR):
            return None
        
        for filename in os.listdir(Config.ICONS_DIR):
            if (filename.upper().startswith(route.upper()) and 
                any(filename.lower().endswith(ext) for ext in Config.IMAGE_EXTENSIONS)):
                icon_path = os.path.join(Config.ICONS_DIR, filename)
                print(f"✓ Found {route} icon: {filename}")
                return icon_path
        
        return None
    
    def _display_image(self, image_path: str, position: Tuple[int, int]) -> bool:
        """Load and display image at specified position"""
        try:
            image_path = '../icons/F_black.png'
            image = Image.open(image_path)
            
            # Resize to standard icon size
            if image.size != Config.ICON_SIZE:
                image = image.resize(Config.ICON_SIZE, Image.Resampling.LANCZOS)
            
            # Ensure RGB format
            if image.mode != 'RGB':
                if image.format == 'PNG':
                    image = image.convert('RGBA')
                else:
                    image = image.convert('RGB')

            self.canvas.SetImage(image, position[0], position[1])
            
        except Exception as e:
            print(f"✗ Error displaying image {image_path}: {e}")
            return False
    
    def _format_arrival_times(self, times: List[str]) -> List[str]:
        """Format arrival times for display"""
        formatted = []
        for time_str in times[:Config.MAX_ARRIVALS]:
            if time_str and time_str != 'No data':
                formatted_time = time_str.replace(' min', 'm').replace('Now', 'NOW')[:3]
                formatted.append(formatted_time)
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
            
            if data['status'] == 'success' and route in data.get('trains', {}):
                route_data = data['trains'][route]
                
                uptown = route_data.get('uptown', {}).get('next_arrivals', [])
                downtown = route_data.get('downtown', {}).get('next_arrivals', [])
                
                self.last_update = datetime.now().strftime('%H:%M:%S')
                print(f"✓ Data updated at {self.last_update}")
                print(f"  Uptown: {uptown}")
                print(f"  Downtown: {downtown}")
                
                return uptown, downtown
            else:
                print(f"✗ No {route} train data available")
                return [], []
                
        except Exception as e:
            print(f"✗ Error fetching real-time data: {e}")
            return [], []
    
    def display_route(self, route: str, uptown_times: List[str], downtown_times: List[str]):
        """Display route information with icon and arrival times"""
        if not self.font:
            print("✗ No font available, cannot display")
            return
        
        self.canvas.Clear()
        
        # Display route icon
        icon_path = self._find_route_icon(route)
        self._display_image(icon_path, Config.FIRST_ICON_POSITION)
        # self._display_image(icon_path, Config.SECOND_ICON_POSITION)

        
        # Station name
        station_name = get_station_name(self.station_id)[:Config.STATION_NAME_MAX_LENGTH]
        self._draw_text(station_name, Config.STATION_NAME_POSITION, Config.WHITE)
        
        # Last update time
        # if self.last_update:
        #     self._draw_text(self.last_update, Config.UPDATE_TIME_POSITION, Config.GRAY)
        
        # Uptown section
        self._draw_text('UPTOWN', Config.UPTOWN_LABEL_POSITION, Config.WHITE)
        uptown_formatted = self._format_arrival_times(uptown_times)
        if uptown_formatted:
            uptown_text = ' '.join(uptown_formatted)
            self._draw_text(uptown_text, Config.UPTOWN_TIMES_POSITION, Config.GREEN)
        
        # Downtown section
        self._draw_text('DOWNTOWN', Config.DOWNTOWN_LABEL_POSITION, Config.WHITE)
        downtown_formatted = self._format_arrival_times(downtown_times)
        if downtown_formatted:
            downtown_text = ' '.join(downtown_formatted)
            self._draw_text(downtown_text, Config.DOWNTOWN_TIMES_POSITION, Config.YELLOW)
        
        # Update display
        self.matrix.SwapOnVSync(self.canvas)
    
    def clear(self):
        """Clear the display"""
        self.canvas.Clear()
        self.matrix.SwapOnVSync(self.canvas)


def run_realtime_display(station_id: str = Config.DEFAULT_STATION, 
                        route: str = Config.DEFAULT_ROUTE):
    """Run real-time MTA display with automatic refresh"""
    print(f"🚇 Starting real-time {route} train display...")
    display = MTALEDDisplay(station_id)
    
    try:
        while True:
            # Fetch fresh data
            uptown, downtown = display.get_realtime_data(route)
            
            # Use fallback if no data
            if not uptown and not downtown:
                print("⚠️ Using fallback data (no real data available)")
                uptown, downtown = ['No', 'Data'], ['Check', 'API']
            
            # Update display
            display.display_route(route, uptown, downtown)
            
            # Wait for next update
            print(f"⏰ Next update in {Config.REFRESH_INTERVAL} seconds... (Ctrl+C to stop)")
            time.sleep(Config.REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        display.clear()
        print(f"\n🛑 {route} train display stopped.")
    except Exception as e:
        display.clear()
        print(f"\n❌ Display error: {e}")


def run_test_display():
    """Run test display with static data"""
    display = MTALEDDisplay()
    
    # Test data
    uptown = ['2 min', '5 min', '8 min']
    downtown = ['Now', '3 min', '6 min']
    
    print("🧪 Running test display...")
    display.display_route(Config.DEFAULT_ROUTE, uptown, downtown)
    
    try:
        print("Press Ctrl+C to stop test...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        display.clear()
        print("\nTest display stopped.")


def show_usage():
    """Display usage information"""
    print("Usage:")
    print("  python3 image_display.py                    # Real-time display (default)")
    print("  python3 image_display.py test               # Test with static data")
    print("  python3 image_display.py realtime [station] [route]  # Custom station/route")
    print()
    print("Examples:")
    print("  python3 image_display.py realtime B10 F     # 57th St F train")
    print("  python3 image_display.py realtime A32 A     # 125th St A train")


def main():
    """Main function with argument parsing"""
    if len(sys.argv) == 1:
        # Default: real-time display
        run_realtime_display()
    elif sys.argv[1] == "test":
        run_test_display()
    elif sys.argv[1] == "realtime":
        station_id = sys.argv[2] if len(sys.argv) > 2 else Config.DEFAULT_STATION
        route = sys.argv[3] if len(sys.argv) > 3 else Config.DEFAULT_ROUTE
        run_realtime_display(station_id, route)
    else:
        show_usage()


if __name__ == "__main__":
    main()