from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timezone
import logging
from google.transit import gtfs_realtime_pb2
import os
from typing import Any, Dict, Iterable, List, Optional
from mta_feeds import FEEDS, ROUTE_TO_FEED
from station_data import load_station_data, is_valid_station, get_default_station, get_station_name, get_station_lines, get_station_direction_codes
from route_data import load_route_data

app = Flask(__name__)

# Load station and route data
STATIONS = load_station_data()
ROUTES = load_route_data()

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
LOG_PATH = os.path.join(LOG_DIR, 'mta_debug.log')
GTFS_HEADERS = {'Accept': 'application/x-google-protobuf'}

def clear_log_file():
    # Clear the log file
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_PATH, 'w') as f:
            f.write('')
    except PermissionError:
        pass  # Skip if can't write to log

def setup_logging():
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        logging.basicConfig(
            filename=LOG_PATH,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    except PermissionError:
        # Fall back to console logging if can't write to file
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

def _normalize_route(route_id: str) -> str:
    route = str(route_id).strip().upper()
    return route[0] if route in {'4X', '5X', '6X'} else route


def _normalize_station_ids(selected_stations: Iterable[Any]) -> List[str]:
    station_ids: List[str] = []
    seen: set[str] = set()
    invalid: List[str] = []

    for raw_station_id in selected_stations:
        station_id = str(raw_station_id).strip().upper()
        if not station_id:
            continue
        if not is_valid_station(station_id):
            invalid.append(station_id)
            continue
        if station_id in seen:
            continue
        seen.add(station_id)
        station_ids.append(station_id)

    if invalid:
        logging.warning(
            "Ignoring invalid station ids in batch request: %s",
            ", ".join(invalid),
        )

    if not station_ids:
        station_ids = [get_default_station()]

    return station_ids


def _normalize_route_list(routes: Iterable[Any]) -> List[str]:
    normalized: List[str] = []
    seen: set[str] = set()
    for raw_route in routes:
        route = _normalize_route(str(raw_route))
        if not route or route in seen:
            continue
        if route not in ROUTE_TO_FEED:
            continue
        seen.add(route)
        normalized.append(route)
    return normalized


def _build_station_routes(
    station_ids: List[str],
    preferred_routes_by_station: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, List[str]]:
    station_routes: Dict[str, List[str]] = {}

    for station_id in station_ids:
        default_routes = _normalize_route_list(get_station_lines(station_id))
        preferred_routes = _normalize_route_list(
            (preferred_routes_by_station or {}).get(station_id, [])
        )

        routes = preferred_routes if preferred_routes else default_routes
        station_routes[station_id] = routes

    return station_routes


def _initialize_route_times_by_station(
    station_routes: Dict[str, List[str]]
) -> Dict[str, Dict[str, Dict[str, set[int]]]]:
    route_times_by_station: Dict[str, Dict[str, Dict[str, set[int]]]] = {}
    for station_id, routes in station_routes.items():
        route_times_by_station[station_id] = {
            route: {'uptown': set(), 'downtown': set()}
            for route in routes
        }
    return route_times_by_station


def _build_stop_to_station_index(station_ids: List[str]) -> Dict[str, List[str]]:
    stop_to_stations: Dict[str, List[str]] = {}
    for station_id in station_ids:
        for stop_id in get_station_direction_codes(station_id):
            stop_to_stations.setdefault(stop_id, []).append(station_id)
    return stop_to_stations


def _build_route_targets(
    station_routes: Dict[str, List[str]]
) -> Dict[str, set[str]]:
    route_targets: Dict[str, set[str]] = {}
    for station_id, routes in station_routes.items():
        for route in routes:
            route_targets.setdefault(route, set()).add(station_id)
    return route_targets


def _get_needed_feed_keys(station_routes: Dict[str, List[str]]) -> List[str]:
    feed_keys = {
        ROUTE_TO_FEED[route]
        for routes in station_routes.values()
        for route in routes
        if route in ROUTE_TO_FEED
    }
    return sorted(feed_keys)


def _process_feed_for_batch(
    feed_url: str,
    current_time: int,
    stop_to_stations: Dict[str, List[str]],
    route_targets: Dict[str, set[str]],
    route_times_by_station: Dict[str, Dict[str, Dict[str, set[int]]]],
) -> Dict[str, set[str]]:
    response = requests.get(feed_url, headers=GTFS_HEADERS, timeout=10)
    response.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    active_routes_by_station: Dict[str, set[str]] = {
        station_id: set() for station_id in route_times_by_station
    }
    for entity in feed.entity:
        if not entity.HasField('trip_update'):
            continue

        trip_update = entity.trip_update
        base_route = _normalize_route(trip_update.trip.route_id)
        target_stations = route_targets.get(base_route)
        if not target_stations:
            continue

        for stop_time_update in trip_update.stop_time_update:
            if not stop_time_update.HasField('arrival'):
                continue

            stop_id = stop_time_update.stop_id
            station_ids_for_stop = stop_to_stations.get(stop_id)
            if not station_ids_for_stop:
                continue

            arrival_time = stop_time_update.arrival.time
            if current_time >= arrival_time:
                continue

            if stop_id.endswith('N'):
                direction = 'uptown'
            elif stop_id.endswith('S'):
                direction = 'downtown'
            else:
                continue

            for station_id in station_ids_for_stop:
                if station_id not in target_stations:
                    continue
                route_times_by_station[station_id][base_route][direction].add(arrival_time)
                active_routes_by_station[station_id].add(base_route)

    return active_routes_by_station

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
    
    train_status = {}
    for route_id, direction_data in route_times.items():
        uptown_times = sorted(list(direction_data['uptown']))[:3]
        downtown_times = sorted(list(direction_data['downtown']))[:3]

        if not uptown_times and not downtown_times:
            continue

        uptown_arrivals = format_arrival_times(uptown_times, current_time)
        downtown_arrivals = format_arrival_times(downtown_times, current_time)
        if uptown_arrivals:
            logging.debug(f"Route {route_id} - Uptown: {uptown_arrivals}")
        if downtown_arrivals:
            logging.debug(f"Route {route_id} - Downtown: {downtown_arrivals}")

        train_status[route_id] = {
            'uptown': {'next_arrivals': uptown_arrivals},
            'downtown': {'next_arrivals': downtown_arrivals},
            'color': ROUTES.get(route_id, {}).get('color', '#808080'),
            'text_color': ROUTES.get(route_id, {}).get('text_color', '#FFFFFF'),
            'name': ROUTES.get(route_id, {}).get('name', f'{route_id} Train')
        }
    return train_status

def get_train_status_batch(
    selected_stations: Iterable[Any],
    preferred_routes_by_station: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Dict[str, Any]]:
    try:
        clear_log_file()
        setup_logging()

        station_ids = _normalize_station_ids(selected_stations)
        station_routes = _build_station_routes(station_ids, preferred_routes_by_station)
        route_times_by_station = _initialize_route_times_by_station(station_routes)
        stop_to_stations = _build_stop_to_station_index(station_ids)
        route_targets = _build_route_targets(station_routes)
        needed_feeds = _get_needed_feed_keys(station_routes)

        current_time = int(datetime.now(timezone.utc).timestamp())
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        for feed_key in needed_feeds:
            try:
                active_routes_by_station = _process_feed_for_batch(
                    FEEDS[feed_key],
                    current_time,
                    stop_to_stations,
                    route_targets,
                    route_times_by_station,
                )
                routes_found = sorted(
                    {
                        route
                        for routes in active_routes_by_station.values()
                        for route in routes
                    }
                )
                logging.debug(f"Found routes in feed {feed_key}: {routes_found}")
            except Exception as feed_error:
                logging.error(f"Error processing feed {feed_key}: {feed_error}")

        station_payloads: Dict[str, Dict[str, Any]] = {}
        for station_id in station_ids:
            train_status = process_route_times(
                route_times_by_station.get(station_id, {}),
                current_time,
                station_id,
            )
            station_payloads[station_id] = {
                'status': 'success',
                'timestamp': timestamp,
                'trains': train_status,
                'active_routes': list(train_status.keys()),
                'station_name': get_station_name(station_id),
            }
        return station_payloads

    except Exception as error:
        logging.error(f"Error: {error}")
        fallback_station_ids = _normalize_station_ids(selected_stations)
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        return {
            station_id: {
                'status': 'error',
                'timestamp': timestamp,
                'trains': {},
                'active_routes': [],
                'station_name': get_station_name(station_id),
            }
            for station_id in fallback_station_ids
        }


def get_train_status(selected_station):
    station_payloads = get_train_status_batch([selected_station])
    if station_payloads:
        return next(iter(station_payloads.values()))
    fallback_station = get_default_station()
    return {
        'status': 'error',
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'trains': {},
        'active_routes': [],
        'station_name': get_station_name(fallback_station),
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
    
    # Get data for selected stations in a single batch refresh.
    station_payloads = get_train_status_batch(selected_stations) if selected_stations else {}
    for station_data in station_payloads.values():
        for route, route_data in station_data.get('trains', {}).items():
            if route not in train_data['trains']:
                train_data['trains'][route] = route_data
    
    # Check if this is an AJAX request
    if request.args.get('ajax') == 'true':
        return jsonify({
            'station_data': train_data,
            'stations': {station_id: STATIONS[station_id] for station_id in selected_stations if station_id in STATIONS}
        })
    
    # Render full page for normal requests
    return render_template('index.html', 
        train_data=train_data, 
        stations=STATIONS, 
        selected_stations=selected_stations
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 
