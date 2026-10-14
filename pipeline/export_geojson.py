import json
import os
import tempfile
import zipfile

import shapefile
from pyproj import Transformer

from config import PROCESSED_DIR, ZONES_ZIP
from load_data import read_lookup

OUTPUT = os.path.join(PROCESSED_DIR, "zones.geojson")


def signed_area(points):
    total = 0.0
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        total += x1 * y2 - x2 * y1
    return total / 2


def to_polygons(shape, transformer):
    points = shape.points
    starts = list(shape.parts) + [len(points)]
    polygons = []
    for i in range(len(starts) - 1):
        part = points[starts[i]:starts[i + 1]]
        lons, lats = transformer.transform([p[0] for p in part], [p[1] for p in part])
        ring = [[round(lon, 5), round(lat, 5)] for lon, lat in zip(lons, lats)]
        if signed_area(part) < 0 or not polygons:
            polygons.append([ring])
        else:
            polygons[-1].append(ring)
    return polygons


def main():
    lookup = read_lookup().set_index("location_id")
    transformer = Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)
    merged = {}

    with tempfile.TemporaryDirectory() as folder:
        with zipfile.ZipFile(ZONES_ZIP) as archive:
            archive.extractall(folder)
        reader = shapefile.Reader(os.path.join(folder, "taxi_zones"))
        names = [f[0] for f in reader.fields[1:]]
        for item in reader.iterShapeRecords():
            location_id = int(dict(zip(names, item.record))["LocationID"])
            if location_id not in lookup.index:
                continue
            merged.setdefault(location_id, []).extend(to_polygons(item.shape, transformer))
        reader.close()

    features = []
    for location_id in sorted(merged):
        info = lookup.loc[location_id]
        features.append({
            "type": "Feature",
            "properties": {
                "location_id": int(location_id),
                "zone": info["zone"],
                "borough": info["borough"],
                "service_zone": info["service_zone"],
            },
            "geometry": {"type": "MultiPolygon", "coordinates": merged[location_id]},
        })

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        json.dump({"type": "FeatureCollection", "features": features}, handle, separators=(",", ":"))
    size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
    print("Zones written:", len(features))
    print("File:", OUTPUT, "({:.1f} MB)".format(size_mb))


if __name__ == "__main__":
    main()
