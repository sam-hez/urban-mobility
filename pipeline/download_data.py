import os
import sys
import urllib.request

from config import RAW_DIR

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/"


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    month = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    file_name = "yellow_tripdata_{}-{:02d}.parquet".format(year, month)
    target = os.path.join(RAW_DIR, file_name)
    if os.path.exists(target):
        print("Already downloaded:", target)
        return
    print("Downloading", BASE_URL + file_name)
    try:
        urllib.request.urlretrieve(BASE_URL + file_name, target)
    except Exception as error:
        if os.path.exists(target):
            os.remove(target)
        print("Download failed:", error)
        print("Get the Yellow Taxi parquet by hand from")
        print("https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page")
        print("and save it in data/raw/")
        sys.exit(1)
    print("Saved to", target)


if __name__ == "__main__":
    main()
