import csv
import os

from flask import Blueprint, jsonify, send_file

from db import database_exists
from settings import CLEANING_SUMMARY_PATH, GEOJSON_PATH

system = Blueprint("system", __name__, url_prefix="/api")


@system.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "database_found": database_exists(),
        "geojson_found": os.path.exists(GEOJSON_PATH),
        "cleaning_summary_found": os.path.exists(CLEANING_SUMMARY_PATH),
    })


@system.route("/zones.geojson")
def zones_geojson():
    if not os.path.exists(GEOJSON_PATH):
        return jsonify({"error": "zones.geojson not found, run pipeline/export_geojson.py"}), 404
    return send_file(GEOJSON_PATH, mimetype="application/geo+json")


@system.route("/cleaning")
def cleaning():
    if not os.path.exists(CLEANING_SUMMARY_PATH):
        return jsonify({"error": "cleaning summary not found, run pipeline/clean_data.py"}), 404
    rows = []
    with open(CLEANING_SUMMARY_PATH, "r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append({
                "reason": row["reason"],
                "action": row["action"],
                "record_count": int(row["record_count"]),
                "percent_of_input": float(row["percent_of_input"]),
                "description": row["description"],
            })
    return jsonify(rows)
