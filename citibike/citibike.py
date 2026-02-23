#!/usr/bin/env python3
"""Legacy compatibility wrapper for Citi Bike service imports."""

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mta_pi_led.services.citibike import (  # noqa: E402
    INFO_URL,
    STATUS_URL,
    get_station_data,
    get_station_info,
    main,
)

__all__ = [
    "INFO_URL",
    "STATUS_URL",
    "get_station_info",
    "get_station_data",
    "main",
]

if __name__ == "__main__":
    main()

