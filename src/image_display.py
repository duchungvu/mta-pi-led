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
        BRIGHTNESS = 25
        MAPPING = 'adafruit-hat'
        GPIO_SLOWDOWN = 5
    
    class Files:
        """File paths for fonts and icons"""
        FONT = '../fonts/tom-thumb.bdf'
        ROUTE_ICON = '../icons/F_black.png'
    
    class Layout:
        """Display layout positions and sizes"""
        ICON_SIZE = (18, 18)
        ICON_POSITION = (1, 7)
        
        STATION_NAME_POSITION = (1, 6)
        
        UPTOWN_LABEL_POSITION = (24, 6)
        UPTOWN_TIMES_POSITION = (24, 11)
        
        DOWNTOWN_LABEL_POSITION = (24, 18)
        DOWNTOWN_TIMES_POSITION = (24, 23)
    
    class Colors:
        """RGB color definitions"""
        WHITE = (255, 255, 255)
        GREEN = (0, 255, 0)
        YELLOW = (255, 255, 0)
    
    class Display:
        """Display behavior settings"""
        MAX_ARRIVALS = 3
        STATION_NAME_MAX_LENGTH = 5
        REFRESH_INTERVAL = 30
    
    class MTA:
        """MTA station and route defaults"""
        STATION = "B10"  # 57th St F train
        ROUTE = "F"


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
    
    def _format_arrival_times(self, times: List[str]) -> List[str]:
        """Format arrival times for display"""
        return [t.replace(' min', 'm').replace('Now', 'NOW')[:3] 
                for t in times[:Config.Display.MAX_ARRIVALS] 
                if t and t != 'No data']
    
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
        self._draw_text(station_name, Config.Layout.STATION_NAME_POSITION, Config.Colors.WHITE)
    
    def _draw_direction(self, direction_name: str, times: List[str], 
                       label_position: Tuple[int, int], times_position: Tuple[int, int],
                       times_color: Tuple[int, int, int]):
        """Draw a direction section: direction name + next 3 arrivals"""
        # Direction label (e.g., "UPTOWN")
        self._draw_text(direction_name, label_position, Config.Colors.WHITE)
        
        # Arrival times (e.g., "2m 5m 8m")
        formatted_times = self._format_arrival_times(times)
        if formatted_times:
            times_text = ' '.join(formatted_times)
            self._draw_text(times_text, times_position, times_color)
    
    def display_route(self, route: str, uptown_times: List[str], downtown_times: List[str]):
        """Display complete MTA board with all components"""
        if not self.font:
            print("✗ No font available, cannot display")
            return
        
        self.canvas.Clear()
        
        # Station Info (line logo + station name)
        self._draw_station_info(route)
        
        # 1st Direction (Uptown)
        self._draw_direction('UPTOWN', uptown_times,
                           Config.Layout.UPTOWN_LABEL_POSITION,
                           Config.Layout.UPTOWN_TIMES_POSITION,
                           Config.Colors.GREEN)
        
        # 2nd Direction (Downtown)
        self._draw_direction('DOWNTOWN', downtown_times,
                           Config.Layout.DOWNTOWN_LABEL_POSITION,
                           Config.Layout.DOWNTOWN_TIMES_POSITION,
                           Config.Colors.YELLOW)
        
        # Update display
        self.matrix.SwapOnVSync(self.canvas)
    
    def clear(self):
        """Clear the display"""
        self.canvas.Clear()
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