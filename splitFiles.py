#!/usr/bin/python3 

import sqlite3
import os
import re
from datetime import datetime, timedelta

# Configuration
SQLITE_DB = 'gps_data.db'
MAX_GAP_TIME = 60  # minutes (default 60 minutes)
OUTPUT_DIR = os.path.expanduser('~/Downloads/processed')

def process_gpx_files():
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Connect to the database
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    # Create the segments table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS gpx_segments (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      gpx_id INTEGER,
                      filename TEXT,
                      start_time TEXT,
                      end_time TEXT,
                      record_count INTEGER,
                      min_lat REAL,
                      max_lat REAL,
                      min_lon REAL,
                      max_lon REAL,
                      FOREIGN KEY(gpx_id) REFERENCES gps_files(id))''')
    
    # Get all files with processingState=0
    cursor.execute("SELECT id, filename FROM gps_files WHERE processingState=0")
    files_to_process = cursor.fetchall()
    
    for file_id, filename in files_to_process:
        try:
            print(f"Processing {filename} (ID: {file_id})...")
            full_path = os.path.join(os.path.expanduser('~/Downloads'), filename)
            
            if not os.path.exists(full_path):
                print(f"File not found: {full_path}")
                continue
            
            # Parse the GPX file
            track_points = parse_gpx_file(full_path)
            
            if not track_points:
                print("No track points found in file")
                mark_as_processed(cursor, file_id, 1)  # Mark as processed
                conn.commit()
                continue
            
            # Split track points into segments based on time gaps
            segments = split_track_points(track_points)
            
            # Process each segment
            base_name = os.path.splitext(filename)[0]
            for i, segment in enumerate(segments, start=1):
                # Get the first and last times in the segment for filename
                first_time_str = segment[0]['time']
                last_time_str = segment[-1]['time']
                
                # Parse the times
                first_time = parse_time(first_time_str)
                last_time = parse_time(last_time_str)
                
                # Format date and time components for filename
                date_time_suffix = ""
                if first_time and last_time:
                    month_day = first_time.strftime('%m%d')  # Two-digit month and day
                    start_time = first_time.strftime('%H%M')  # Start time (HHMM)
                    end_time = last_time.strftime('%H%M')     # End time (HHMM)
                    date_time_suffix = f"_{month_day}_{start_time}-{end_time}"
                elif first_time:
                    month_day = first_time.strftime('%m%d')
                    start_time = first_time.strftime('%H%M')
                    date_time_suffix = f"_{month_day}_{start_time}-0000"
                elif last_time:
                    end_time = last_time.strftime('%H%M')
                    date_time_suffix = "_0000_0000-{end_time}"
                else:
                    date_time_suffix = "_0000_0000-0000"
                
                output_filename = f"{base_name}{date_time_suffix}.{i:03d}.csv"
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                
                # Save segment to CSV and get stats
                stats = save_to_csv(segment, output_path)
                
                # Insert segment info into database
                cursor.execute('''INSERT INTO gpx_segments 
                                (gpx_id, filename, start_time, end_time, record_count,
                                 min_lat, max_lat, min_lon, max_lon)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                             (file_id, output_filename, stats['start_time'], 
                              stats['end_time'], stats['count'],
                              stats['min_lat'], stats['max_lat'],
                              stats['min_lon'], stats['max_lon']))
                
                print(f"Saved segment {i} to {output_path} with {stats['count']} points")
            
            # Mark original file as processed
            mark_as_processed(cursor, file_id, 1)
            conn.commit()
            print(f"Finished processing {filename}")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            # Mark as error state (2)
            mark_as_processed(cursor, file_id, 2)
            conn.commit()
    
    conn.close()

def parse_gpx_file(file_path):
    track_points = []
    in_trkpt = False
    current_point = {}
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Check for track point start
            if line.startswith('<trkpt'):
                in_trkpt = True
                current_point = {}
                
                # Extract latitude and longitude
                lat_match = re.search(r'lat="([^"]+)"', line)
                lon_match = re.search(r'lon="([^"]+)"', line)
                if lat_match and lon_match:
                    current_point['lat'] = float(lat_match.group(1))
                    current_point['lon'] = float(lon_match.group(1))
                continue
            
            if not in_trkpt:
                continue
            
            # Extract other fields
            if line.startswith('<ele>'):
                current_point['ele'] = float(line.replace('<ele>', '').replace('</ele>', ''))
            elif line.startswith('<time>'):
                current_point['time'] = line.replace('<time>', '').replace('</time>', '')
            elif line.startswith('<speed>'):
                current_point['speed'] = float(line.replace('<speed>', '').replace('</speed>', ''))
            elif line.startswith('<name>'):
                current_point['name'] = line.replace('<name>', '').replace('</name>', '')
            elif line.startswith('</trkpt>'):
                # End of track point
                if 'lat' in current_point and 'lon' in current_point and 'time' in current_point:
                    track_points.append(current_point)
                in_trkpt = False
    
    return track_points

def parse_time(time_str):
    try:
        return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        try:
            return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            return None

def split_track_points(track_points):
    if not track_points:
        return []
    
    segments = []
    current_segment = []
    prev_time = None
    
    for point in track_points:
        if not point.get('time'):
            continue  # Skip points without timestamps
        
        current_time = parse_time(point['time'])
        if not current_time:
            continue
        
        if prev_time is None:
            # First point in segment
            current_segment.append(point)
        else:
            time_diff = (current_time - prev_time).total_seconds() / 60  # in minutes
            
            if time_diff > MAX_GAP_TIME:
                # Time gap exceeds threshold, start new segment
                if current_segment:
                    segments.append(current_segment)
                current_segment = [point]
            else:
                # Continue current segment
                current_segment.append(point)
        
        prev_time = current_time
    
    # Add the last segment
    if current_segment:
        segments.append(current_segment)
    
    return segments

def save_to_csv(segment, output_path):
    stats = {
        'count': 0,
        'start_time': None,
        'end_time': None,
        'min_lat': None,
        'max_lat': None,
        'min_lon': None,
        'max_lon': None
    }
    
    with open(output_path, 'w') as f:
        # Write header
        f.write("latitude,longitude,elevation,timestamp,speed,name\n")
        
        # Write data points and collect stats
        for i, point in enumerate(segment):
            line = [
                str(point.get('lat', '')),
                str(point.get('lon', '')),
                str(point.get('ele', '')),
                point.get('time', ''),
                str(point.get('speed', '')),
                f'"{point.get("name", "")}"'  # Quote names in case they contain commas
            ]
            f.write(','.join(line) + '\n')
            
            # Update stats
            if i == 0:
                stats['start_time'] = point['time']
                stats['min_lat'] = point['lat']
                stats['max_lat'] = point['lat']
                stats['min_lon'] = point['lon']
                stats['max_lon'] = point['lon']
            else:
                stats['min_lat'] = min(stats['min_lat'], point['lat'])
                stats['max_lat'] = max(stats['max_lat'], point['lat'])
                stats['min_lon'] = min(stats['min_lon'], point['lon'])
                stats['max_lon'] = max(stats['max_lon'], point['lon'])
            
            stats['end_time'] = point['time']
            stats['count'] += 1
    
    return stats

def mark_as_processed(cursor, file_id, state):
    cursor.execute("UPDATE gps_files SET processingState=? WHERE id=?", (state, file_id))

if __name__ == "__main__":
    process_gpx_files()
