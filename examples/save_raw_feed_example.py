import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime, timezone
from google.transit import gtfs_realtime_pb2
import json
from google.protobuf.json_format import MessageToJson
from mta_feeds import FEEDS

def save_raw_feed_example():
    # Process all available feeds
    for feed_key, feed_url in FEEDS.items():
        print(f"\nFetching feed: {feed_key}")
        
        try:
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
            
            # Create examples directory if it doesn't exist
            os.makedirs('examples', exist_ok=True)
            
            with open(filename, 'w') as f:
                # Parse and re-dump to get pretty formatting
                json.dump(json.loads(json_str), f, indent=2)
            
            print(f"✓ Raw feed saved to: {filename}")
            
            # Print basic feed info
            entity_count = len(feed.entity)
            trip_updates = sum(1 for e in feed.entity if e.HasField('trip_update'))
            vehicle_positions = sum(1 for e in feed.entity if e.HasField('vehicle'))
            alerts = sum(1 for e in feed.entity if e.HasField('alert'))
            
            print(f"  Total entities: {entity_count}")
            print(f"  Trip updates: {trip_updates}")
            print(f"  Vehicle positions: {vehicle_positions}")
            print(f"  Service alerts: {alerts}")
            
        except Exception as e:
            print(f"✗ Error processing feed {feed_key}: {str(e)}")

if __name__ == '__main__':
    save_raw_feed_example() 