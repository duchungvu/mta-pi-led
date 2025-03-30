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

This document explains the structure of the MTA GTFS-realtime feed data.

## Feed Structure

The feed contains an array of entities, where each entity represents a train's current status and upcoming stops.

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

### Stop Time Updates
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

## Stop ID Mappings

### N, R, W Trains
- R01N: Times Square (Northbound)
- R02N: 49th St (Northbound)
- R03N: 57th St (Northbound)
- R04N: 5th Ave (Northbound)
- R05N: Lexington Ave (Northbound)
- R06N: 59th St (Northbound)
- R07N: Queensboro Plaza (Northbound)
- R08N: 39th Ave (Northbound)
- R09N: 36th Ave (Northbound)
- R10N: Steinway St (Northbound)
- R11N: 46th St (Northbound)
- R12N: Northern Blvd (Northbound)
- R13N: 65th St (Northbound)
- R14N: 71st Ave (Northbound)
- R15N: 75th Ave (Northbound)
- R16N: Continental Ave (Northbound)
- R17N: 169th St (Northbound)
- R18N: 179th St (Northbound)
- R19N: Jamaica Center (Northbound)

### 4, 5, 6 Trains
- 635N: 125th St (Northbound)
- 636N: 116th St (Northbound)
- 637N: 110th St (Northbound)
- 638N: 103rd St (Northbound)
- 639N: 96th St (Northbound)
- 640N: 86th St (Northbound)
- 641N: 77th St (Northbound)
- 642N: 68th St (Northbound)
- 643N: 59th St (Northbound)
- 644N: 51st St (Northbound)
- 645N: Grand Central (Northbound)
- 646N: 33rd St (Northbound)
- 647N: 28th St (Northbound)
- 648N: 23rd St (Northbound)
- 649N: 14th St (Northbound)
- 650N: Astor Place (Northbound)
- 651N: Bleecker St (Northbound)
- 652N: Spring St (Northbound)
- 653N: Canal St (Northbound)
- 654N: Brooklyn Bridge (Northbound)
- 655N: Fulton St (Northbound)
- 656N: Wall St (Northbound)
- 657N: Bowling Green (Northbound)

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
- The feed provides real-time updates, so times may change between updates
- Stop sequences are ordered from current location to final destination 