#!/usr/bin/env python3
import csv
import sys
import os
from datetime import datetime, timedelta

def parse_time(timestr):
    return datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%SZ")

def format_time(dt):
    return dt.strftime("%H%M")

def format_mmdd(dt):
    return dt.strftime("%m%d")

def split_csv_by_time_gap(filename, max_gap_seconds):
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    if not rows:
        print("No data rows found.")
        return

    base_name = os.path.splitext(os.path.basename(filename))[0]
    gps_prefix = base_name.split('_')[0]

    current_group = []
    previous_time = None
    file_count = 0

    for row in rows:
        current_time = parse_time(row["Time"])

        if previous_time is None or (current_time - previous_time).total_seconds() <= max_gap_seconds:
            current_group.append(row)
        else:
            if current_group:
                write_segment(current_group, gps_prefix)
            current_group = [row]

        previous_time = current_time

    if current_group:
        write_segment(current_group, gps_prefix)

def write_segment(rows, gps_prefix):
    start_time = parse_time(rows[0]["Time"])
    end_time = parse_time(rows[-1]["Time"])
    mmdd = format_mmdd(start_time)
    start_hhmm = format_time(start_time)
    end_hhmm = format_time(end_time)

    out_filename = f"{gps_prefix}_{mmdd}_{start_hhmm}-{end_hhmm}.csv"

    with open(out_filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Time", "Latitude", "Longitude", "Name", "Elevation", "Speed"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote: {out_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python split_gps.py gps06_something.csv max_gap_seconds")
        sys.exit(1)

    filename = sys.argv[1]
    max_gap_seconds = int(sys.argv[2])
    split_csv_by_time_gap(filename, max_gap_seconds)
