from datetime import datetime, timezone
import os
from typing import Any

from flask import Flask, jsonify, render_template, request

from mta_pi_led.services.mta_arrivals import get_train_status, get_train_status_batch
from station_data import load_station_data

app = Flask(__name__)

# Load station data for the legacy station picker page.
STATIONS = load_station_data()


@app.route("/")
def index() -> Any:
    # Get stations from query params
    selected_stations = request.args.getlist("stations")

    # Get data for selected stations in a single batch refresh.
    train_data = {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "trains": {},
    }

    station_payloads = (
        get_train_status_batch(selected_stations) if selected_stations else {}
    )
    for station_data in station_payloads.values():
        for route, route_data in station_data.get("trains", {}).items():
            if route not in train_data["trains"]:
                train_data["trains"][route] = route_data

    # Check if this is an AJAX request
    if request.args.get("ajax") == "true":
        return jsonify(
            {
                "station_data": train_data,
                "stations": {
                    station_id: STATIONS[station_id]
                    for station_id in selected_stations
                    if station_id in STATIONS
                },
            }
        )

    # Render full page for normal requests
    return render_template(
        "index.html",
        train_data=train_data,
        stations=STATIONS,
        selected_stations=selected_stations,
    )


if __name__ == "__main__":
    try:
        port = int(os.getenv("WEB_PORT", "8080"))
    except ValueError:
        port = 8080
    app.run(host="0.0.0.0", port=port, debug=True)
