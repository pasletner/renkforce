#!/usr/bin/python3
import subprocess

import os

def discover_devices():
    devices = []
    path = '/dev/serial/by-id'
    
    # Check if the directory exists
    if not os.path.exists(path):
        print("Directory '/dev/serial/by-id' does not exist.")
        return devices

    # Get the list of devices (files in the directory)
    for device in os.listdir(path):
        # Construct the full device path
        device_path = os.path.join(path, device)
        if os.path.islink(device_path):
            devices.append(device)
    
    return devices

# Example usage:
devices = discover_devices()
#iint(devices)


import re

from datetime import datetime

def get_current_date_time():
    # Get current date and time, then format it
    return datetime.now().strftime("%Y-%m-%d_%H:%M")


def extract_serial_number(device_name):
    # Pattern to match serial number in names like 'usb-STMicroelectronics_STM32_Virtual_COM_Port_0A7831533334-if00'
    match = re.search(r'_(\w{12})-if\d+', device_name)
    if match:
        return match.group(1)
    else:
        print(f"Serial number not found in device name: {device_name}")
        return None

import subprocess

def run_gpsbabel( input_device, output_format, output_file, baud_rate=38400, init_baud=38400):
    # Construct the command
    input_option = f"skytraq,initbaud={init_baud},baud={baud_rate}"
    command = [
        "/usr/bin/gpsbabel",
        "-i", input_option,
        "-f", input_device,
        "-o", output_format,
        "-F", output_file
    ]
    
    # Run the command
    try:
        subprocess.run(command, check=True)
        print(f"GPS Babel successfully executed. Output saved to {output_file}.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running gpsbabel: {e}")

     
# Example usage:
#device_name = 'usb-STMicroelectronics_STM32_Virtual_COM_Port_0A7831533334-if00'
#serial_number = extract_serial_number(device_name)
#print(serial_number)

def translate_serial_to_name(serial_number, filename):
    # Open the file containing the serial-to-name mapping
    try:
        with open(filename, 'r') as file:
            for line in file:
                # Split the line into serial_number and device_name
                parts = line.strip().split()
                if len(parts) == 2:
                    file_serial, device_name = parts
                    if file_serial == serial_number:
                        return device_name
        print(f"Serial number {serial_number} not found in the file.")
        return None
    except FileNotFoundError:
        print(f"File {filename} not found.")
        return None

# Example usage:
#serial_number = '0A7831533334'

#device_name = 'usb-STMicroelectronics_STM32_Virtual_COM_Port_0A7831533334-if00'
devices = discover_devices()
print(f"Starting ")
for device in devices:

    serial_number = extract_serial_number(device)
#    filename = '/usr/share/pas/serial_device_mapping.txt'  # This should be the file you are working with
    filename='/home/sletner/Documents/GPSBABEL/src/serial_device_mapping.txt'	
    device_name = translate_serial_to_name(serial_number, filename)
    print(f"Trying to suck from  {device_name}")
    #actual=os.path.realpath(device)
    #print(f"Real path is {device}")

#    arguments=f"-i skytraq,initbaud=38400,baud=38400 -f {device}  -o gpx -F {device_name}_test.gpx"
     #arguments=
    now=get_current_date_time()   
    filename_out=f"/home/sletner/Downloads/gps_logs/{device_name}_{now}_track.gpx"
#    print(f"Running with args: '{arguments}'")
#    subprocess.run(["/usr/bin/gpsbabel",'-i skytraq,initbaud=38400,baud=38400',f"-f {device}","-o gpx", f"-F {filename_out}"]);
    # Example usage
    run_gpsbabel(
        input_device=f"/dev/serial/by-id/{device}",
        output_format="gpx",
        output_file=filename_out
    )
