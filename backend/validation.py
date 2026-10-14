from datetime import datetime, timedelta
from database import query_all


class ApiError(Exception):
    def __init__(self, message, status=400, field=None):
        super().__init__(message)
        self.message = message        
        self.status = status        
        self.field = field

def get_int(args, name, minimum, maximum, default=None):
    raw = args.get(name)
    if raw is None or raw == "":
        return default 
    try:
        value = int(raw)
    except ValueError:
        raise ApiError(f"'{name}' must be a whole number", field=name)
    if value < minimum or value > maximum:
        raise ApiError(f"'{name}' must be between {minimum} and {maximum}", field=name)
    return value

def get_float(args, name, minimum, maximum):
    raw = args.get(name)
    if raw is None or raw == "":
        return None    
    try:
        value = float(raw)
    except ValueError:
        raise ApiError(f"'{name}' must be a number", field=name)
    if value != value or value < minimum or value > maximum:   
        raise ApiError(f"'{name}' must be between {minimum} and {maximum}", field=name)
    return value

def get_date(args, name):
    raw = args.get(name)
    if raw is None or raw == "":
        return None 
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        raise ApiError(f"'{name}' must be a date written as YYYY-MM-DD", field=name)


def get_choice(args, name, choices, default):
    value = args.get(name, default)
    if value not in choices:
        raise ApiError(f"'{name}' must be one of: {', '.join(choices)}", field=name)
    return value

def build_filters(args, skip=()):
    conditions = []
    params = {}

    start = get_date(args, "start_date")
    end = get_date(args, "end_date")
    if start and end and start > end:
        raise ApiError("'start_date' must not be after 'end_date'", field="start_date")
    if start:
        conditions.append("t.pickup_datetime >= :start_date")
        params["start_date"] = start.strftime("%Y-%m-%d")
    if end:
        conditions.append("t.pickup_datetime < :end_date_next")
        params["end_date_next"] = (end + timedelta(days=1)).strftime("%Y-%m-%d")

    if "pickup_zone_id" not in skip:
        zone = get_int(args, "pickup_zone_id", 1, 265)
        if zone is not None:
            conditions.append("t.pickup_location_id = :pickup_zone_id")
            params["pickup_zone_id"] = zone   
    if "dropoff_zone_id" not in skip:
        zone = get_int(args, "dropoff_zone_id", 1, 265)
        if zone is not None:
            conditions.append("t.dropoff_location_id = :dropoff_zone_id")
            params["dropoff_zone_id"] = zone
    
    borough = args.get("pickup_borough")
    if borough:
        names = [row["borough_name"] for row in                
                query_all("SELECT borough_name FROM boroughs", use_cache=True)]
        if borough not in names:
            raise ApiError(f"'pickup_borough' must be one of: {', '.join(names)}", field="pickup_borough")
        conditions.append(
            "t.pickup_location_id IN (SELECT z.location_id FROM zones z "
            "JOIN boroughs b ON b.borough_id = z.borough_id WHERE b.borough_name = :pickup_borough)")
        params["pickup_borough"] = borough

    min_distance = get_float(args, "min_distance", 0, 100)
    max_distance = get_float(args, "max_distance", 0, 100)
    if min_distance is not None and max_distance is not None and min_distance > max_distance:
        raise ApiError("'min_distance' must not be larger than 'max_distance'", field="min_distance")
    if min_distance is not None:
        conditions.append("t.trip_distance >= :min_distance")
        params["min_distance"] = min_distance
    if max_distance is not None:
        conditions.append("t.trip_distance <= :max_distance")
        params["max_distance"] = max_distance

    min_fare = get_float(args, "min_fare", 0, 1000)
    max_fare = get_float(args, "max_fare", 0, 1000)
    if min_fare is not None and max_fare is not None and min_fare > max_fare:
        raise ApiError("'min_fare' must not be larger than 'max_fare'", field="min_fare")
    if min_fare is not None:
        conditions.append("t.total_amount >= :min_fare")
        params["min_fare"] = min_fare
    if max_fare is not None:
        conditions.append("t.total_amount <= :max_fare")
        params["max_fare"] = max_fare

    payment = get_int(args, "payment_type_id", 0, 255)
    if payment is not None:
        conditions.append("t.payment_type_id = :payment_type_id")
        params["payment_type_id"] = payment

    return conditions, params


def make_where(conditions):
    if not conditions:
        return ""
    return " WHERE " + " AND ".join(conditions)