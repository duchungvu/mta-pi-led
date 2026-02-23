#!/usr/bin/env python3
"""
Simple Citi Bike availability checker.
Gets bike, e-bike, and dock availability for a given station.
"""

import requests
from typing import Dict, Optional, Tuple

INFO_URL = 'https://gbfs.citibikenyc.com/gbfs/en/station_information.json'
STATUS_URL = 'https://gbfs.citibikenyc.com/gbfs/en/station_status.json' 

def get_station_info(station_name: str) -> Dict:
    """
    Get the ID of a Citi Bike station by its name.
    """
    info_response = requests.get(INFO_URL, timeout=10)
    stations_info = info_response.json()['data']['stations']
    for station in stations_info:
        if station['name'] == station_name:
            return station
        
    raise ValueError(f"Station not found: {station_name}")


def get_station_data(id: str) -> Optional[Dict]:
    """
    Get status for a Citi Bike station.
    
    Args:
        id: Station ID
        
    Returns:
        Dict with 'bikes', 'ebikes', 'docks' or None if not found
    """
    status_response = requests.get(STATUS_URL, timeout=10)
    
    if status_response.status_code != 200:
        return None
        
    station_data = status_response.json()['data']['stations']

    for station in station_data:
        if station['station_id'] == id:
            return station

def main():
    station_info = get_station_info("W 56 St & 6 Ave")
    print(f"Station Info: {station_info}")
        
    station_data = get_station_data(station_info['station_id'])
    print(f"Station Data: {station_data}")


if __name__ == "__main__":
    main()

