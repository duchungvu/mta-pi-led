from flask import Flask, render_template
import requests
from datetime import datetime, timezone
import logging
from google.transit import gtfs_realtime_pb2
import os
from mta_feeds import FEEDS, ROUTE_TO_FEED

app = Flask(__name__)

def clear_log_file():
    # Clear the log file
    with open('mta_debug.log', 'w') as f:
        f.write('')

def get_train_status():
    try:
        # Clear log file before processing
        clear_log_file()
        
        # Set up logging
        logging.basicConfig(
            filename='mta_debug.log',
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Initialize train status
        train_status = {
            route: {
                'uptown': {'status': 'No data', 'next_arrivals': []},
                'downtown': {'status': 'No data', 'next_arrivals': []}
            } for route in ['4', '5', '6', 'N', 'R', 'W']
        }
        
        # Track arrival times for each route and direction
        route_times = {
            route: {'uptown': set(), 'downtown': set()} 
            for route in ['4', '5', '6', 'N', 'R', 'W']
        }
        
        # Get unique feed URLs we need
        needed_feeds = set(ROUTE_TO_FEED[route] for route in ['4', '5', '6', 'N', 'R', 'W'])
        
        # Process each feed
        for feed_key in needed_feeds:
            feed_url = FEEDS[feed_key]
            # Fetch GTFS-realtime feed
            response = requests.get(
                feed_url, 
                headers={
                    'Accept': 'application/x-google-protobuf'
                }
            )
            response.raise_for_status()
            
            # Parse the feed
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            
            # Get current time in UTC
            current_time = int(datetime.now(timezone.utc).timestamp())
            
            # Process each entity in the feed
            route_ids = set()  # Track all route IDs we see
            for entity in feed.entity:
                if not entity.HasField('trip_update'):
                    continue
                    
                trip_update = entity.trip_update
                route_id = trip_update.trip.route_id
                
                # Handle both regular and express variants
                base_route = route_id[0] if route_id in ['4X', '5X', '6X'] else route_id
                if base_route not in ['4', '5', '6', 'N', 'R', 'W']:
                    continue
                    
                route_ids.add(route_id)
                
                # Process each stop time update for all trains
                for stop_time_update in trip_update.stop_time_update:
                    # We're only interested in 59th St station
                    # 4,5,6 trains use 629N/629S
                    # N,R,W trains use R11N/R11S
                    if stop_time_update.stop_id in ['629N', '629S', 'R11N', 'R11S']:
                        # Process arrival and departure times
                        for time_field in ['arrival', 'departure']:
                            if not stop_time_update.HasField(time_field):
                                continue
                                
                            time = getattr(stop_time_update, time_field).time
                            minutes_away = (time - current_time) / 60
                            
                            # Only consider future times within 30 minutes
                            # Add a small buffer to handle times that are slightly in the past
                            if current_time - 60 < time <= current_time + 1800:  # 30 minutes = 1800 seconds
                                if stop_time_update.stop_id in ['629N', 'R11N']:
                                    route_times[base_route]['uptown'].add(time)
                                elif stop_time_update.stop_id in ['629S', 'R11S']:
                                    route_times[base_route]['downtown'].add(time)
            
            # Log all route IDs we found
            logging.debug(f"Found routes in feed {feed_key}: {sorted(list(route_ids))}")
        
        # Process times for each route
        for route_id in ['4', '5', '6', 'N', 'R', 'W']:
            for direction in ['uptown', 'downtown']:
                # Convert set to sorted list and get the next 3 arrivals
                times = sorted(list(route_times[route_id][direction]))[:3]
                if times:
                    # Calculate minutes away and format display
                    next_arrivals = []
                    for t in times:
                        minutes = (t - current_time) / 60
                        if minutes < 1:
                            next_arrivals.append('Now')
                        else:
                            # Round up to nearest minute
                            minutes = int(minutes + 0.5)
                            next_arrivals.append(f'{minutes} min')
                    
                    train_status[route_id][direction] = {
                        'next_arrivals': next_arrivals
                    }
                    
                    # Log final selected times
                    logging.debug(f"Route {route_id} - {direction.capitalize()}: {next_arrivals}")
        
        return {
            'status': 'success',
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'trains': train_status
        }
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        # Return a dictionary with the same structure but with error status
        return {
            'status': 'error',
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'trains': {
                route: {
                    'uptown': {'next_arrivals': ['Error loading data']},
                    'downtown': {'next_arrivals': ['Error loading data']}
                } for route in ['4', '5', '6', 'N', 'R', 'W']
            }
        }

@app.route('/')
def index():
    train_data = get_train_status()
    return render_template('index.html', train_data=train_data)

if __name__ == '__main__':
    app.run(debug=True) 