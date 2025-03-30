import csv
import json
from collections import defaultdict

# Read stops.txt
stations = {}
with open('gtfs_subway/stops.txt', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Only process parent stations (location_type == 1)
        if row['location_type'] == '1':
            station_id = row['stop_id']
            stations[station_id] = {
                'name': row['stop_name'],
                'lines': [],
                'direction_codes': []
            }
        # Add direction codes to parent stations
        elif row['parent_station'] in stations:
            stations[row['parent_station']]['direction_codes'].append(row['stop_id'])

# Read MTA_SUBWAYS station csv to get line information
station_lines = defaultdict(set)
with open('examples/MTA_Subway_Stations_20250330.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        station_id = row['GTFS Stop ID']
        # Get line codes from Daytime Routes column
        lines = row['Daytime Routes'].split()
        if station_id in stations:
            station_lines[station_id].update(lines)

# Add lines to each station
for station_id, station_data in stations.items():
    station_data['lines'] = sorted(list(station_lines[station_id]))

# Write to JSON file
with open('mta_stations.json', 'w') as f:
    json.dump(stations, f, indent=2) 