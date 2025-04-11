# MTA Train Status

A real-time NYC subway train tracker application that displays upcoming train arrivals for stations across the MTA system.

> **Note:** This application was generated with assistance from [Cursor](https://cursor.sh/), an AI-powered code editor.

![MTA Train Status App](https://via.placeholder.com/800x450.png?text=MTA+Train+Status+App)

## Features

- 🚇 Real-time train arrival information for all MTA subway stations
- 🔍 Search and add multiple stations to monitor simultaneously
- 🎨 Visually accurate NYC subway line colors and styling
- 🔄 Refresh individual stations or all stations at once
- ⏱️ Visual indicators for imminent train arrivals
- 📱 Responsive design that works on desktop and mobile devices

## Prerequisites

- Python 3.6 or higher
- Flask
- Protobuf and Google Transit libraries
- Internet connection to access MTA's real-time data feeds

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/mta-train-status.git
   cd mta-train-status
   ```

2. Install the required dependencies:
   ```
   pip install flask requests google-transit-realtime-feed-parser protobuf
   ```

## Running the Application

1. Start the Flask application:
   ```
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

3. By default, the application will load with no stations selected. Search for and select stations to see train arrivals.

## Sharing with Friends

### Local Network
To make the app accessible on your local network:
1. The app is already configured to run on all network interfaces (`0.0.0.0`)
2. Find your local IP address:
   - On Mac: Run `ifconfig | grep "inet " | grep -v 127.0.0.1`
   - On Windows: Run `ipconfig`
3. Share the URL `http://YOUR_IP_ADDRESS:5000` with friends on the same network

### Remote Access with ngrok
To share the app with friends outside your network:
1. Install ngrok: https://ngrok.com/download
2. Run ngrok to create a tunnel to your local server:
   ```
   ngrok http 5000
   ```
3. Share the HTTPS URL provided by ngrok with your friends
4. Note: Free tier ngrok URLs expire after a few hours

## Hosting on Raspberry Pi

### Installation on Raspberry Pi

1. **Update system packages**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Python and dependencies**:
   ```bash
   sudo apt install -y python3-pip python3-venv
   ```

3. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/mta-pi-led.git
   cd mta-pi-led
   ```

4. **Set up a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install required packages**:
   ```bash
   pip install flask requests gtfs-realtime-bindings protobuf
   ```

### Auto-start on Boot

Create a systemd service to run the app automatically on startup:

1. Create a systemd service file:
   ```bash
   sudo nano /etc/systemd/system/mta-status.service
   ```

2. Add the following content (replace USERNAME with your actual username):
   ```
   [Unit]
   Description=MTA Train Status App
   After=network.target

   [Service]
   User=USERNAME
   WorkingDirectory=/home/USERNAME/mta-pi-led
   ExecStart=/home/USERNAME/mta-pi-led/venv/bin/python app.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl enable mta-status.service
   sudo systemctl start mta-status.service
   ```

4. Check status:
   ```bash
   sudo systemctl status mta-status.service
   ```

## Using the Application

### Adding Stations
1. Use the search box to find stations by name or subway line
2. Click on a station in the dropdown to add it to your dashboard
3. The station card will appear with real-time arrival information

### Managing Stations
- Click on a station chip at the top to quickly scroll to that station
- Click the "×" button on a station card to remove it
- Click "Refresh this station" to update just that station's data
- Click "Refresh All" to update all stations

### Understanding the Display
- **Now**: Trains arriving immediately (red background)
- **1-2 min**: Trains arriving very soon (orange text)
- **3+ min**: Regular upcoming trains

## How It Works

The application connects to the MTA's GTFS-Realtime feeds to retrieve real-time subway information. It processes this data to display upcoming train arrivals for each selected station, organized by line and direction.

## Configuration

Station and route data are loaded from configuration files in the project. The application refreshes automatically every 30 seconds to keep the information current.

## Next Steps

1. Integrate with LED matrix display
2. Add mobile app for remote control
3. Implement real-time updates using WebSocket

## License

[MIT License](LICENSE)

## Acknowledgements

- MTA for providing real-time data feeds
- The GTFS-Realtime specification
- NYC Transit for the iconic subway line styling

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