from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timezone
import logging
from google.transit import gtfs_realtime_pb2
import os
from mta_feeds import FEEDS, ROUTE_TO_FEED
from station_data import load_station_data, is_valid_station, get_default_station, get_station_name, get_station_lines, get_station_direction_codes
from route_data import load_route_data

app = Flask(__name__)

# Load station and route data
STATIONS = load_station_data()
ROUTES = load_route_data()

def clear_log_file():
    # Clear the log file
    with open('mta_debug.log', 'w') as f:
        f.write('')

def setup_logging():
    logging.basicConfig(
        filename='mta_debug.log',
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def initialize_train_status(selected_station):
    if not is_valid_station(selected_station):
        selected_station = get_default_station()
    
    return {
        route: {
            'uptown': {'status': 'No data', 'next_arrivals': []},
            'downtown': {'status': 'No data', 'next_arrivals': []},
            'color': ROUTES.get(route, {}).get('color', '#808080'),
            'text_color': ROUTES.get(route, {}).get('text_color', '#FFFFFF'),
            'name': ROUTES.get(route, {}).get('name', f'{route} Train')
        } for route in get_station_lines(selected_station)
    }

def initialize_route_times(selected_station):
    if not is_valid_station(selected_station):
        selected_station = get_default_station()
    
    return {
        route: {'uptown': set(), 'downtown': set()} 
        for route in get_station_lines(selected_station)
    }

def get_needed_feeds(selected_station):
    if not is_valid_station(selected_station):
        selected_station = get_default_station()
    
    return set(ROUTE_TO_FEED[route] for route in get_station_lines(selected_station))

def process_stop_time_update(stop_time_update, current_time, route_times, base_route, selected_station):
    if not is_valid_station(selected_station):
        selected_station = get_default_station()
    
    direction_codes = get_station_direction_codes(selected_station)
    if stop_time_update.stop_id in direction_codes:
        # Only process arrival times
        if not stop_time_update.HasField('arrival'):
            return
            
        time = stop_time_update.arrival.time
        
        # Only include future times
        if current_time < time:
            # Add to appropriate direction based on stop ID
            if stop_time_update.stop_id.endswith('N'):  # Northbound/Uptown
                route_times[base_route]['uptown'].add(time)
            elif stop_time_update.stop_id.endswith('S'):  # Southbound/Downtown
                route_times[base_route]['downtown'].add(time)

def process_feed(feed_url, route_times, current_time, selected_station):
    if not is_valid_station(selected_station):
        selected_station = get_default_station()
    
    response = requests.get(
        feed_url, 
        headers={
            'Accept': 'application/x-google-protobuf'
        }
    )
    response.raise_for_status()
    
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    
    route_ids = set()
    for entity in feed.entity:
        if not entity.HasField('trip_update'):
            continue
            
        trip_update = entity.trip_update
        route_id = trip_update.trip.route_id
        
        base_route = route_id[0] if route_id in ['4X', '5X', '6X'] else route_id
        if base_route not in get_station_lines(selected_station):
            continue
            
        route_ids.add(route_id)
        
        for stop_time_update in trip_update.stop_time_update:
            process_stop_time_update(stop_time_update, current_time, route_times, base_route, selected_station)
    
    return route_ids

def format_arrival_times(times, current_time):
    next_arrivals = []
    for t in times:
        minutes = (t - current_time) / 60
        if minutes < 1:
            next_arrivals.append('Now')
        else:
            minutes = int(minutes + 0.5)
            next_arrivals.append(f'{minutes} min')
    return next_arrivals

def process_route_times(route_times, current_time, selected_station):
    if not is_valid_station(selected_station):
        selected_station = get_default_station()
    
    train_status = initialize_train_status(selected_station)
    for route_id in get_station_lines(selected_station):
        for direction in ['uptown', 'downtown']:
            times = sorted(list(route_times[route_id][direction]))[:3]
            if times:
                next_arrivals = format_arrival_times(times, current_time)
                train_status[route_id][direction] = {
                    'next_arrivals': next_arrivals
                }
                logging.debug(f"Route {route_id} - {direction.capitalize()}: {next_arrivals}")
    return train_status

def get_train_status(selected_station):
    try:
        clear_log_file()
        setup_logging()
        
        # Validate station code
        if not is_valid_station(selected_station):
            selected_station = get_default_station()
            logging.warning(f"Invalid station code provided. Using default station: {selected_station}")
        
        train_status = initialize_train_status(selected_station)
        route_times = initialize_route_times(selected_station)
        needed_feeds = get_needed_feeds(selected_station)
        current_time = int(datetime.now(timezone.utc).timestamp())
        
        for feed_key in needed_feeds:
            feed_url = FEEDS[feed_key]
            route_ids = process_feed(feed_url, route_times, current_time, selected_station)
            logging.debug(f"Found routes in feed {feed_key}: {sorted(list(route_ids))}")
        
        train_status = process_route_times(route_times, current_time, selected_station)
        
        return {
            'status': 'success',
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'trains': train_status,
            'station_name': get_station_name(selected_station)
        }
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return {
            'status': 'error',
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'trains': {
                route: {
                    'uptown': {'next_arrivals': ['Error loading data']},
                    'downtown': {'next_arrivals': ['Error loading data']},
                    'color': ROUTES.get(route, {}).get('color', '#808080'),
                    'text_color': ROUTES.get(route, {}).get('text_color', '#FFFFFF'),
                    'name': ROUTES.get(route, {}).get('name', f'{route} Train')
                } for route in get_station_lines(get_default_station())
            },
            'station_name': get_station_name(selected_station)
        }

@app.route('/')
def index():
    # Get stations from query params
    selected_stations = request.args.getlist('stations')
    
    # Don't use default station - keep empty if no stations provided
    # if not selected_stations:
    #     selected_stations = [get_default_station()]
    
    # Get data for each station
    train_data = {
        'status': 'success',
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'trains': {}
    }
    
    # Get data for each station and merge train data
    for station_id in selected_stations:
        if is_valid_station(station_id):
            station_data = get_train_status(station_id)
            
            # Merge train data
            if 'trains' in station_data:
                for route, route_data in station_data['trains'].items():
                    if route not in train_data['trains']:
                        train_data['trains'][route] = route_data
    
    # Check if this is an AJAX request
    if request.args.get('ajax') == 'true':
        return jsonify(train_data)
    
    # Regular request returns HTML
    return render_template('index.html', 
                          train_data=train_data, 
                          stations=STATIONS, 
                          selected_stations=selected_stations)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 