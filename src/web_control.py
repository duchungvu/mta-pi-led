#!/usr/bin/env python3
"""Board controller web API."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from flask import Flask, jsonify, render_template, request

from mta_pi_led.services.board_control import (
    build_schedule_preview,
    list_stations,
    load_board_runtime_status,
    load_config_payload,
    normalize_config_payload,
    save_config_payload,
)

app = Flask(__name__)


@app.get("/")
def index() -> Any:
    return render_template("web_control.html")


@app.get("/api")
def api_index() -> Any:
    return jsonify(
        {
            "name": "mta-pi-led board controller",
            "version": "v1",
            "endpoints": [
                "GET /api/stations",
                "GET /api/board/config",
                "PUT /api/board/config",
                "GET /api/board/schedule",
                "GET /api/board/status",
            ],
        }
    )


@app.get("/api/stations")
def get_stations() -> Any:
    query = request.args.get("q", "")
    stations = list_stations(query=query)
    return jsonify(
        {
            "count": len(stations),
            "stations": stations,
        }
    )


@app.get("/api/board/config")
def get_board_config() -> Any:
    raw_payload = load_config_payload()
    config, _, warnings = normalize_config_payload(raw_payload, strict=False)
    schedule = build_schedule_preview(config)
    return jsonify(
        {
            "config": config,
            "schedule_preview": schedule,
            "warnings": warnings,
            "generated_at": _utc_now(),
        }
    )


@app.put("/api/board/config")
def update_board_config() -> Any:
    incoming = request.get_json(silent=True)
    if not isinstance(incoming, dict):
        return (
            jsonify(
                {
                    "status": "error",
                    "errors": ["Expected a JSON object in request body."],
                }
            ),
            400,
        )

    current_payload = load_config_payload()
    current_config, _, _ = normalize_config_payload(current_payload, strict=False)
    normalized, errors, _ = normalize_config_payload(incoming, strict=True)

    expected_version = incoming.get("version")
    current_version = current_config["version"]
    if expected_version is not None:
        try:
            expected_version_int = int(expected_version)
        except (TypeError, ValueError):
            expected_version_int = -1
        if expected_version_int != current_version:
            return (
                jsonify(
                    {
                        "status": "error",
                        "errors": [
                            "Config version mismatch. Refresh and retry your changes."
                        ],
                        "current_version": current_version,
                    }
                ),
                409,
            )

    if errors:
        return jsonify({"status": "error", "errors": errors}), 400

    normalized["version"] = current_version + 1
    save_config_payload(normalized)

    schedule = build_schedule_preview(normalized)
    return jsonify(
        {
            "status": "ok",
            "config": normalized,
            "schedule_preview": schedule,
            "updated_at": _utc_now(),
        }
    )


@app.get("/api/board/schedule")
def get_board_schedule() -> Any:
    raw_payload = load_config_payload()
    config, _, warnings = normalize_config_payload(raw_payload, strict=False)
    schedule = build_schedule_preview(config)
    return jsonify(
        {
            "config": config,
            "schedule_preview": schedule,
            "warnings": warnings,
            "generated_at": _utc_now(),
        }
    )


@app.get("/api/board/status")
def get_board_status() -> Any:
    status = load_board_runtime_status()
    if status is None:
        return jsonify(
            {
                "status": "unknown",
                "message": "Board heartbeat not available yet.",
                "updated_at": _utc_now(),
            }
        )
    return jsonify({"status": "ok", "board": status, "updated_at": _utc_now()})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


if __name__ == "__main__":
    try:
        port = int(os.getenv("WEB_PORT", "5000"))
    except ValueError:
        port = 5000
    debug_enabled = os.getenv("WEB_DEBUG", "0") == "1"
    reloader_enabled = os.getenv("WEB_RELOADER", "0") == "1"
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_enabled,
        use_reloader=reloader_enabled,
    )
