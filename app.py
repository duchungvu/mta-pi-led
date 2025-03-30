from flask import Flask, render_template, request
import requests
from datetime import datetime, timezone
import logging
from google.transit import gtfs_realtime_pb2
import os
from mta_feeds import FEEDS, ROUTE_TO_FEED

app = Flask(__name__)

# Station configurations
STATIONS = {
    'lexington_59': {
        'name': 'Lexington Av/59 St (N, R, W)',
        'stops': ['R11N', 'R11S'],
        'routes': ['N', 'R', 'W']
    },
    '59_st': {
        'name': '59 St (4, 5, 6)',
        'stops': ['629N', '629S'],
        'routes': ['4', '5', '6']
    }
}

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
    return {
        route: {
            'uptown': {'status': 'No data', 'next_arrivals': []},
            'downtown': {'status': 'No data', 'next_arrivals': []}
        } for route in STATIONS[selected_station]['routes']
    }

def initialize_route_times(selected_station):
    return {
        route: {'uptown': set(), 'downtown': set()} 
        for route in STATIONS[selected_station]['routes']
    }

def get_needed_feeds(selected_station):
    return set(ROUTE_TO_FEED[route] for route in STATIONS[selected_station]['routes'])

def process_stop_time_update(stop_time_update, current_time, route_times, base_route, selected_station):
    if stop_time_update.stop_id in STATIONS[selected_station]['stops']:
        for time_field in ['arrival', 'departure']:
            if not stop_time_update.HasField(time_field):
                continue
                
            time = getattr(stop_time_update, time_field).time
            minutes_away = (time - current_time) / 60
            
            if current_time - 60 < time <= current_time + 1800:  # 30 minutes = 1800 seconds
                if stop_time_update.stop_id in [STATIONS[selected_station]['stops'][0]]:  # First stop is uptown
                    route_times[base_route]['uptown'].add(time)
                elif stop_time_update.stop_id in [STATIONS[selected_station]['stops'][1]]:  # Second stop is downtown
                    route_times[base_route]['downtown'].add(time)

def process_feed(feed_url, route_times, current_time, selected_station):
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
        if base_route not in STATIONS[selected_station]['routes']:
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
    train_status = initialize_train_status(selected_station)
    for route_id in STATIONS[selected_station]['routes']:
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
            'station_name': STATIONS[selected_station]['name']
        }
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return {
            'status': 'error',
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'trains': {
                route: {
                    'uptown': {'next_arrivals': ['Error loading data']},
                    'downtown': {'next_arrivals': ['Error loading data']}
                } for route in STATIONS[selected_station]['routes']
            },
            'station_name': STATIONS[selected_station]['name']
        }

@app.route('/')
def index():
    selected_station = request.args.get('station', 'lexington_59')  # Default to Lexington/59
    train_data = get_train_status(selected_station)
    return render_template('index.html', train_data=train_data, stations=STATIONS, selected_station=selected_station)

if __name__ == '__main__':
    app.run(debug=True) 