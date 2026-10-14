import time

import database
from app import app

RUNS = 3   # each endpoint is called this many times


def main():
    client = app.test_client()
    day = client.get("/api/filters").get_json()["min_date"][:10]   # a day that exists in the data

    urls = [
        "/api/summary",
        f"/api/summary?start_date={day}&end_date={day}",
        "/api/trips",
        "/api/trips?sort_by=total_amount&order=desc",
        "/api/trips?sort_by=trip_distance&min_distance=5",
        f"/api/trips?pickup_zone_id=161&start_date={day}&end_date={day}",
        "/api/trips?pickup_borough=Brooklyn&min_fare=20&max_fare=60",
        "/api/trips?page=1000&per_page=100",
        "/api/zones/161",
        "/api/charts/hourly",
        "/api/charts/daily",
        "/api/charts/boroughs",
        "/api/charts/top-zones",
        "/api/charts/top-zones?by=dropoff",
        "/api/charts/payment-types",
        "/api/charts/distance-distribution",
    ]

    print(f"{'first':>7} {'best':>7}  endpoint   (seconds, best of {RUNS})")
    for url in urls:
        times = []
        for _ in range(RUNS):
            database._cache.clear()
            start = time.time()
            response = client.get(url)
            times.append(time.time() - start)
            if response.status_code != 200:
                print(f"  !! {url} returned {response.status_code}")
                break
        print(f"{times[0]:7.2f} {min(times):7.2f}  {url}")


if __name__ == "__main__":
    main()