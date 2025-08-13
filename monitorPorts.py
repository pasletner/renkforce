#!/usr/bin/python3


import os
import re
import time
import hashlib
import sqlite3
from datetime import datetime
import subprocess
from threading import Thread

# Configuration
SERIAL2NAME_FILE = 'serial2name.txt'
GPX_FILE = '/tmp/last.gpx'
SQLITE_DB = 'gps_data.db'
DESTINATION_CATALOG = os.path.expanduser('~/Downloads')
PROCESS_DATA_SCRIPT = 'doThings.sh'
CHECK_INTERVAL = 5  # seconds between checks

def monitor_serial_ports():
    # Initialize the database
    init_db()
    
    # Get initial list of devices
    previous_devices = get_serial_devices()
    
    while True:
        try:
            current_devices = get_serial_devices()
            new_devices = [d for d in current_devices if d not in previous_devices]
            
            for device in new_devices:
                serial_number = extract_serial_number(device)
                if serial_number:
                    gps_name = get_gps_name(serial_number)
                    if gps_name:
                        print(f"Found new device: {device} with GPS name: {gps_name}")
                        process_device(device, gps_name)
            
            previous_devices = current_devices
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("Monitoring stopped by user")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(CHECK_INTERVAL)

def get_serial_devices():
    try:
        devices = os.listdir('/dev/serial/by-id')
        return [d for d in devices if os.path.islink(f'/dev/serial/by-id/{d}')]
    except FileNotFoundError:
        return []

def extract_serial_number(device_name):
    # Look for 12 hex digits in the device name
    match = re.search(r'([0-9A-Fa-f]{12})', device_name)
    return match.group(1).upper() if match else None

def get_gps_name(serial_number):
    try:
        with open(SERIAL2NAME_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if parts and parts[0] == serial_number:
                    return parts[1]
    except FileNotFoundError:
        print(f"Warning: {SERIAL2NAME_FILE} not found")
    return None

def process_device(device_name, gps_name):
    device_path = f'/dev/serial/by-id/{device_name}'
    
    # Run gpsbabel command
    cmd = ['gpsbabel', '-i', 'skytraq,baud=38400,initbaud=38400', 
           '-f', device_path, '-o', 'gpx', '-F', GPX_FILE]
    subprocess.run(cmd, check=True)
    
    if not os.path.exists(GPX_FILE):
        print(f"Error: {GPX_FILE} not created")
        return
    
    # Process the GPX file
    try:
        # Read and remove line 3
        with open(GPX_FILE, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 3:
            print("Error: GPX file too short")
            return
            
        time_line = lines[2].strip()
        del lines[2]
        
        # Write back the modified file
        with open(GPX_FILE, 'w') as f:
            f.writelines(lines)
            
        # Calculate MD5 hash
        md5_hash = calculate_md5(GPX_FILE)
        
        # Check if file exists in database
        if not file_exists_in_db(md5_hash):
            # Extract timestamp from the removed line
            timestamp = extract_timestamp(time_line)
            if timestamp:
                # Create destination filename
                dest_filename = create_destination_filename(gps_name, timestamp)
                dest_path = os.path.join(DESTINATION_CATALOG, dest_filename)
                
                # Copy file
                os.system(f'cp {GPX_FILE} {dest_path}')
                
                # Add to database with full timestamp
                add_to_db(dest_filename, md5_hash, time_line)
                print(f"Saved new GPS data to {dest_path}")
                
                # Start background processing
                start_background_processing(dest_path)
            else:
                print("Could not extract timestamp from GPX file")
        else:
            print("File already exists in database, skipping")
            
    except subprocess.CalledProcessError as e:
        print(f"gpsbabel command failed: {e}")
    except Exception as e:
        print(f"Error processing GPX file: {e}")

def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def extract_timestamp(time_line):
    # Extract timestamp from line like "<time>2025-07-19T20:51:40.564Z</time>"
    match = re.search(r'<time>(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})', time_line)
    if match:
        date_part = match.group(1)
        time_part = f"{match.group(2)}{match.group(3)}"
        
        # Parse the date to get day of month
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        day = dt.strftime("%d")
        
        return (day, time_part)
    return None

def create_destination_filename(gps_name, timestamp):
    day, time_str = timestamp
    # Remove any '#' from gps_name and replace with nothing
    clean_name = gps_name.replace('#', '')
    return f"{clean_name}_{day}{time_str}.gpx"

def init_db():
    conn = sqlite3.connect(SQLITE_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS gps_files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT UNIQUE,
                  md5_hash TEXT UNIQUE,
                  timestamp TEXT,
                  processingState INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def file_exists_in_db(md5_hash):
    conn = sqlite3.connect(SQLITE_DB)
    c = conn.cursor()
    c.execute("SELECT 1 FROM gps_files WHERE md5_hash=?", (md5_hash,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def add_to_db(filename, md5_hash, timestamp):
    conn = sqlite3.connect(SQLITE_DB)
    c = conn.cursor()
    c.execute("INSERT INTO gps_files (filename, md5_hash, timestamp) VALUES (?, ?, ?)", 
              (filename, md5_hash, timestamp))
    conn.commit()
    conn.close()

def start_background_processing(file_path):
    def run_processing_script():
        try:
            script_path = os.path.expanduser(PROCESS_DATA_SCRIPT)
            if os.path.exists(script_path):
                subprocess.Popen([script_path, file_path])
                print(f"Started background processing with: {script_path} {file_path}")
            else:
                print(f"Warning: Processing script {script_path} not found")
        except Exception as e:
            print(f"Error starting background process: {e}")
    
    # Start in a separate thread to avoid blocking
    Thread(target=run_processing_script).start()

if __name__ == "__main__":
    monitor_serial_ports()
