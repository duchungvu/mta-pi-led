# MTA Train Status Display

This project displays real-time status information for the 4, 5, and 6 trains at the 59th St/Lexington Ave station. It's designed to be displayed on a Raspberry Pi with an LED matrix, but can also be viewed in a web browser.

## Prerequisites

- Python 3.7 or higher

## Setup

1. Clone this repository
2. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   .\venv\Scripts\activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. Make sure your virtual environment is activated (you should see `(venv)` in your terminal prompt)
2. Start the Flask application:
   ```bash
   python app.py
   ```
3. Open your web browser and navigate to `http://localhost:5000`

## Project Structure

- `app.py`: Main Flask application
- `templates/index.html`: HTML template for displaying train status
- `requirements.txt`: Python dependencies
- `venv/`: Virtual environment directory (created during setup)

## Next Steps

1. Integrate with LED matrix display
2. Add mobile app for remote control
3. Implement real-time updates using WebSocket 

# MTA GTFS-realtime Feed Structure

This document explains the structure of the MTA GTFS-realtime feed data. For the complete specification and detailed field descriptions, please refer to:
- [Official GTFS-realtime documentation](https://gtfs.org/documentation/realtime/reference)
- [MTA GTFS-realtime documentation](https://www.mta.info/document/134521)

## Feed Overview

The MTA GTFS-realtime feed provides real-time information about train locations and arrival times. The feed is updated every 30 seconds and contains two types of entities for each train:

1. `tripUpdate`: Contains information about upcoming stops and arrival/departure times
2. `vehicle`: Contains real-time information about where a train currently is

Each train run will have both a `tripUpdate` entity (showing upcoming stops) and a `vehicle` entity (showing current position).

### Entity Level
```json
{
  "id": "000001N",  // Unique identifier for this train update
  "tripUpdate": {
    "trip": {
      "tripId": "141325_N..N",     // Format: HHMMSS_Route..Direction
      "startTime": "23:35:10",     // Scheduled start time of the train run
      "startDate": "20250327",     // Date of the train run (YYYYMMDD)
      "routeId": "N"               // Route identifier (N, R, W, 4, 5, 6, etc.)
    },
    "stopTimeUpdate": [            // Array of upcoming stops
      {
        "arrival": {
          "time": "1743138152"     // Unix timestamp for arrival
        },
        "departure": {
          "time": "1743138152"     // Unix timestamp for departure
        },
        "stopId": "R05N"          // Stop identifier
      }
    ]
  }
}
```

### Vehicle Entity
```json
{
  "id": "000002N",
  "vehicle": {
    "trip": {
      "tripId": "138950_N..N",     // Format: HHMMSS_Route..Direction
      "startTime": "23:12:07",     // Scheduled start time of the train run
      "startDate": "20250327",     // Date of the train run (YYYYMMDD)
      "routeId": "N"               // Route identifier (N, R, W, 4, 5, 6, etc.)
    },
    "currentStopSequence": 37,     // Sequence number of the current stop
    "currentStatus": "STOPPED_AT", // Current status of the train
    "timestamp": "1743136640",     // When this position was recorded
    "stopId": "R08N"              // Current stop ID where the train is located
  }
}
```

## Field Descriptions

### Entity ID
- `id`: A unique identifier for each train update in the feed
- Format: Usually a combination of numbers and route letter (e.g., "000001N")

### Trip Information
- `tripId`: Unique identifier for the train run
  - Format: `HHMMSS_Route..Direction`
  - Example: "141325_N..N" means:
    - Started at 14:13:25
    - N train
    - Northbound direction
- `startTime`: The scheduled start time of the train run (HH:MM:SS)
- `startDate`: The date of the train run in YYYYMMDD format
- `routeId`: The route identifier (N, R, W, 4, 5, 6, etc.)

### Stop Time Updates (tripUpdate entity)
Each stop in the `stopTimeUpdate` array contains:
- `arrival`: Time when the train will arrive at the stop
  - `time`: Unix timestamp for arrival
- `departure`: Time when the train will depart from the stop
  - `time`: Unix timestamp for departure
- `stopId`: Unique identifier for the station
  - Format: `[Route][Number][Direction]`
  - Example: "R05N" means:
    - R train route
    - 5th station in sequence
    - Northbound direction

### Vehicle Information (vehicle entity)
- `currentStopSequence`: The sequence number of the current stop in the train's route
- `currentStatus`: The current status of the train
  - "STOPPED_AT": Train is currently stopped at a station
  - "INCOMING_AT": Train is approaching a station
  - "IN_TRANSIT_TO": Train is moving to a station
  - "OUT_OF_SERVICE": Train is not in service
- `timestamp`: Unix timestamp when this position was recorded
- `stopId`: The current stop ID where the train is located

## Time Format
- All arrival and departure times are provided in Unix timestamps
- To convert to human-readable time:
  ```python
  from datetime import datetime
  timestamp = 1743138152
  human_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
  ```

## Notes
- When arrival and departure times are the same, it indicates the train is not dwelling at the station
- The feed provides real-time updates every 30 seconds
- Stop sequences are ordered from current location to final destination
- Each train run may have both a `tripUpdate` entity (showing upcoming stops) and a `vehicle` entity (showing current position) 