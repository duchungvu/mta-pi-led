import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime, timezone
from google.transit import gtfs_realtime_pb2
import json
from google.protobuf.json_format import MessageToJson
from mta_feeds import FEEDS, ROUTE_TO_FEED

def save_raw_feed_example():
    # Get unique feed URLs we need
    needed_feeds = set(ROUTE_TO_FEED[route] for route in ['4', '5', '6', 'N', 'R', 'W'])
    
    # Process each feed
    for feed_key in needed_feeds:
        feed_url = FEEDS[feed_key]
        print(f"Fetching feed: {feed_key}")
        
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
        
        # Convert protobuf message to JSON
        json_str = MessageToJson(feed)
        
        # Save to file
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f'examples/raw_feed_{feed_key}_{timestamp}.json'
        
        with open(filename, 'w') as f:
            # Parse and re-dump to get pretty formatting
            json.dump(json.loads(json_str), f, indent=2)
        
        print(f"Raw feed saved to: {filename}")

if __name__ == '__main__':
    save_raw_feed_example() 