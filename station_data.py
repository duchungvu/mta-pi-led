import json

# Global variable to store station data
_station_data = None

def load_station_data():
    """Load station data from JSON file and return it."""
    global _station_data
    if _station_data is None:
        try:
            with open('mta_stations.json', 'r') as f:
                _station_data = json.load(f)
        except FileNotFoundError:
            raise Exception("Station data file (mta_stations.json) not found. Please run create_station_db.py first.")
    return _station_data

def is_valid_station(station_id):
    """Check if a station ID is valid."""
    stations = load_station_data()
    return station_id in stations

def get_default_station():
    """Return a default station ID (first one in the database)."""
    stations = load_station_data()
    # Return the first station ID or a known major station
    return next(iter(stations.keys()))

def get_station_name(station_id):
    """Get the name of a station by its ID."""
    stations = load_station_data()
    if station_id not in stations:
        raise ValueError(f"Invalid station ID: {station_id}")
    return stations[station_id]['name']

def get_station_lines(station_id):
    """Get the lines that serve a station."""
    stations = load_station_data()
    if station_id not in stations:
        raise ValueError(f"Invalid station ID: {station_id}")
    return stations[station_id]['lines']

def get_station_direction_codes(station_id):
    """Get the direction codes for a station."""
    stations = load_station_data()
    if station_id not in stations:
        raise ValueError(f"Invalid station ID: {station_id}")
    return stations[station_id]['direction_codes'] 