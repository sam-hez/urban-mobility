from flask import Blueprint, jsonify, request

import config
from database import query_all
from validation import ApiError, build_filters, get_choice, get_int, make_where

api = Blueprint("api", __name__, url_prefix="/api")

SORT_COLUMNS = {
    "pickup_datetime": "t.pickup_datetime",
    "trip_distance": "t.trip_distance",
    "total_amount": "t.total_amount",
}

ZONE_COLUMNS = {"pickup": "t.pickup_location_id", "dropoff": "t.dropoff_location_id"}

TRIP_JOINS = """
    JOIN zones pz        ON pz.location_id = t.pickup_location_id
    JOIN boroughs pb     ON pb.borough_id = pz.borough_id
    JOIN zones dz        ON dz.location_id = t.dropoff_location_id
    JOIN boroughs db     ON db.borough_id = dz.borough_id
    JOIN payment_types p ON p.payment_type_id = t.payment_type_id
"""

@api.route("/health")
def health():
    try:
        version = query_all("SELECT VERSION() AS version")[0]["version"]
    except Exception:
        return jsonify({"status": "error", "database": "unreachable"}), 503
    return jsonify({"status": "ok", "database": "connected", "mysql_version": version})


@api.route("/filters")
def filter_options():
    ranges = query_all(
        "SELECT MIN(pickup_datetime) AS min_date, MAX(pickup_datetime) AS max_date, "
        "MAX(trip_distance) AS max_distance, MAX(total_amount) AS max_fare FROM trips",
        use_cache=True)[0]
    boroughs = query_all("SELECT borough_name FROM boroughs ORDER BY borough_name", use_cache=True)
    payments = query_all(
        "SELECT payment_type_id, description FROM payment_types ORDER BY payment_type_id",
        use_cache=True)
    return jsonify({
        "min_date": ranges["min_date"],
        "max_date": ranges["max_date"],
        "max_distance": ranges["max_distance"],
        "max_fare": ranges["max_fare"],
        "boroughs": [row["borough_name"] for row in boroughs],
        "payment_types": payments,
    })


@api.route("/summary")
def summary():
    conditions, params = build_filters(request.args)
    sql = f"""
        SELECT COUNT(*)                               AS total_trips,
               ROUND(SUM(t.total_amount), 2)          AS total_revenue,
               ROUND(AVG(t.total_amount), 2)          AS avg_total,
               ROUND(AVG(t.fare_amount), 2)           AS avg_fare,
               ROUND(AVG(t.trip_distance), 2)         AS avg_distance_miles,
               ROUND(AVG(t.duration_min), 2)          AS avg_duration_min,
               ROUND(AVG(t.tip_amount), 2)            AS avg_tip,
               ROUND(SUM(t.trip_distance) / NULLIF(SUM(t.duration_min), 0) * 60, 2) AS avg_speed_mph
        FROM trips t {make_where(conditions)}
    """
    return jsonify(query_all(sql, params, use_cache=True)[0])


@api.route("/trips")
def trips():
    conditions, params = build_filters(request.args)
    sort_by = get_choice(request.args, "sort_by", list(SORT_COLUMNS), "pickup_datetime")
    order = get_choice(request.args, "order", ["asc", "desc"], "desc")
    page = get_int(request.args, "page", 1, config.MAX_PAGE, default=1)
    per_page = get_int(request.args, "per_page", 1, config.MAX_PER_PAGE, default=config.DEFAULT_PER_PAGE)

    where = make_where(conditions)
    total = query_all(f"SELECT COUNT(*) AS total FROM trips t {where}", params, use_cache=True)[0]["total"]

    order_by = f"{SORT_COLUMNS[sort_by]} {order}, t.trip_id {order}"

    sql = f"""
        SELECT t.trip_id, t.pickup_datetime, t.dropoff_datetime,
               t.pickup_location_id, pz.zone_name AS pickup_zone, pb.borough_name AS pickup_borough,
               t.dropoff_location_id, dz.zone_name AS dropoff_zone, db.borough_name AS dropoff_borough,
               t.passenger_count, t.trip_distance, t.duration_min,
               t.fare_amount, t.tip_amount, t.tolls_amount, t.total_amount,
               p.description AS payment_type
        FROM (SELECT t.trip_id FROM trips t {where}
              ORDER BY {order_by} LIMIT :limit OFFSET :offset) page
        JOIN trips t ON t.trip_id = page.trip_id
        {TRIP_JOINS}
        ORDER BY {order_by}
    """
    rows = query_all(sql, {**params, "limit": per_page, "offset": (page - 1) * per_page})
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,
        "sort_by": sort_by,
        "order": order,
        "trips": rows,
    })


@api.route("/trips/<int:trip_id>")
def trip_detail(trip_id):
    sql = f"""
        SELECT t.*, pz.zone_name AS pickup_zone, pb.borough_name AS pickup_borough,
               dz.zone_name AS dropoff_zone, db.borough_name AS dropoff_borough,
               p.description AS payment_type
        FROM trips t
        {TRIP_JOINS}
        WHERE t.trip_id = :trip_id
    """
    rows = query_all(sql, {"trip_id": trip_id})
    if not rows:
        raise ApiError(f"Trip {trip_id} was not found", status=404)
    return jsonify(rows[0])


@api.route("/zones")
def zones():
    sql = """
        SELECT z.location_id, z.zone_name, b.borough_name AS borough,
               s.service_zone_name AS service_zone, z.centroid_lat, z.centroid_lon
        FROM zones z
        JOIN boroughs b      ON b.borough_id = z.borough_id
        JOIN service_zones s ON s.service_zone_id = z.service_zone_id
        ORDER BY z.location_id
    """
    return jsonify(query_all(sql, use_cache=True))


@api.route("/zones/<int:zone_id>")
def zone_detail(zone_id):
    info = query_all(
        "SELECT z.location_id, z.zone_name, b.borough_name AS borough, "
        "s.service_zone_name AS service_zone, z.centroid_lat, z.centroid_lon "
        "FROM zones z JOIN boroughs b ON b.borough_id = z.borough_id "
        "JOIN service_zones s ON s.service_zone_id = z.service_zone_id "
        "WHERE z.location_id = :zone_id", {"zone_id": zone_id}, use_cache=True)
    if not info:
        raise ApiError(f"Zone {zone_id} was not found", status=404)

    conditions, params = build_filters(request.args, skip=("pickup_zone_id", "dropoff_zone_id"))
    params["zone_id"] = zone_id
    pickup_where = make_where(conditions + ["t.pickup_location_id = :zone_id"])
    dropoff_where = make_where(conditions + ["t.dropoff_location_id = :zone_id"])

    pickups = query_all(
        "SELECT COUNT(*) AS trips, ROUND(AVG(t.total_amount), 2) AS avg_total, "
        f"ROUND(AVG(t.trip_distance), 2) AS avg_distance_miles FROM trips t {pickup_where}",
        params, use_cache=True)[0]
    dropoffs = query_all(
        f"SELECT COUNT(*) AS trips FROM trips t {dropoff_where}", params, use_cache=True)[0]
    destinations = query_all(f"""
        SELECT z.location_id, z.zone_name, c.trips
        FROM (SELECT t.dropoff_location_id AS zone_id, COUNT(*) AS trips
              FROM trips t {pickup_where}
              GROUP BY t.dropoff_location_id ORDER BY trips DESC LIMIT 5) c
        JOIN zones z ON z.location_id = c.zone_id
        ORDER BY c.trips DESC
    """, params, use_cache=True)

    return jsonify({"zone": info[0], "pickups": pickups, "dropoffs": dropoffs,
                    "top_destinations": destinations})



@api.route("/charts/hourly")
def chart_hourly():
    conditions, params = build_filters(request.args)
    rows = query_all(f"""
        SELECT HOUR(t.pickup_datetime) AS hour, COUNT(*) AS trips,
               ROUND(AVG(t.fare_amount), 2) AS avg_fare,
               ROUND(AVG(t.trip_distance), 2) AS avg_distance_miles
        FROM trips t {make_where(conditions)}
        GROUP BY HOUR(t.pickup_datetime)
    """, params, use_cache=True)
    by_hour = {row["hour"]: row for row in rows}
    empty = {"trips": 0, "avg_fare": None, "avg_distance_miles": None}
    return jsonify([by_hour.get(h, {"hour": h, **empty}) for h in range(24)])


@api.route("/charts/daily")
def chart_daily():
    conditions, params = build_filters(request.args)
    rows = query_all(f"""
        SELECT DATE(t.pickup_datetime) AS day, COUNT(*) AS trips,
               ROUND(SUM(t.total_amount), 2) AS revenue
        FROM trips t {make_where(conditions)}
        GROUP BY DATE(t.pickup_datetime)
        ORDER BY day
    """, params, use_cache=True)
    return jsonify(rows)


@api.route("/charts/boroughs")
def chart_boroughs():
    conditions, params = build_filters(request.args)
    rows = query_all(f"""
        SELECT b.borough_name AS borough, COUNT(*) AS trips
        FROM trips t
        JOIN zones z    ON z.location_id = t.pickup_location_id
        JOIN boroughs b ON b.borough_id = z.borough_id
        {make_where(conditions)}
        GROUP BY b.borough_id, b.borough_name
        ORDER BY trips DESC
    """, params, use_cache=True)
    return jsonify(rows)


@api.route("/charts/top-zones")
def chart_top_zones():
    conditions, params = build_filters(request.args)
    by = get_choice(request.args, "by", list(ZONE_COLUMNS), "pickup")
    limit = get_int(request.args, "limit", 1, config.MAX_TOP_LIMIT, default=10)
    rows = query_all(f"""
        SELECT z.location_id, z.zone_name, b.borough_name AS borough, c.trips
        FROM (SELECT {ZONE_COLUMNS[by]} AS zone_id, COUNT(*) AS trips
              FROM trips t {make_where(conditions)}
              GROUP BY {ZONE_COLUMNS[by]} ORDER BY trips DESC LIMIT :limit) c
        JOIN zones z    ON z.location_id = c.zone_id
        JOIN boroughs b ON b.borough_id = z.borough_id
        ORDER BY c.trips DESC
    """, {**params, "limit": limit}, use_cache=True)
    return jsonify(rows)


@api.route("/charts/payment-types")
def chart_payment_types():
    conditions, params = build_filters(request.args)
    rows = query_all(f"""
        SELECT p.payment_type_id, p.description AS payment_type, COUNT(*) AS trips
        FROM trips t
        JOIN payment_types p ON p.payment_type_id = t.payment_type_id
        {make_where(conditions)}
        GROUP BY p.payment_type_id, p.description
        ORDER BY trips DESC
    """, params, use_cache=True)
    return jsonify(rows)


@api.route("/charts/distance-distribution")
def chart_distance_distribution():
    conditions, params = build_filters(request.args)
    rows = query_all(f"""
        SELECT CASE WHEN t.trip_distance < 1  THEN '0-1'
                    WHEN t.trip_distance < 2  THEN '1-2'
                    WHEN t.trip_distance < 5  THEN '2-5'
                    WHEN t.trip_distance < 10 THEN '5-10'
                    WHEN t.trip_distance < 20 THEN '10-20'
                    ELSE '20+' END AS bucket,
               COUNT(*) AS trips
        FROM trips t {make_where(conditions)}
        GROUP BY bucket
    """, params, use_cache=True)
    counts = {row["bucket"]: row["trips"] for row in rows}
    labels = ["0-1", "1-2", "2-5", "5-10", "10-20", "20+"]
    return jsonify([{"bucket": label, "trips": counts.get(label, 0)} for label in labels])
