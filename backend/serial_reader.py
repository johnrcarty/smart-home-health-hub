# serial_reader.py

import os
import time
import serial
from dotenv import load_dotenv

from state_manager import update_sensor, set_serial_mode

load_dotenv()

# SERIAL CONFIG (override in your .env if needed)
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
BAUD_RATE   = int(os.getenv("BAUD_RATE", 115200))


def connect_serial():
    """
    Attempt to open the serial port. If it fails, wait 5s and retry.
    Once open, flip state_manager into serial mode.
    """
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"[serial_reader] Connected to {SERIAL_PORT} @ {BAUD_RATE} baud")
            set_serial_mode(True)
            return ser
        except Exception as e:
            print(f"[serial_reader] Could not open {SERIAL_PORT}: {e}. Retrying in 5s…")
            set_serial_mode(False)
            time.sleep(5)


def serial_loop():
    """
    Main loop for reading USB serial data.
    On SerialException (device unplugged), flips out of serial mode
    and retries connect_serial().
    """
    ser = connect_serial()

    while True:
        try:
            raw = ser.readline().decode("ascii", errors="ignore").strip()
            if not raw:
                continue

            parts = raw.split()
            if len(parts) < 5:
                print(f"[serial_reader] Skipping invalid line: {raw}")
                continue

            # Parse fields: timestamp, spo2, bpm, pa, status…
            # e.g. "2025-06-26 12:34:56 98* 75* 1.2 OK"
            spo2_str = parts[2].rstrip("*")
            bpm_str  = parts[3].rstrip("*")
            pa_str   = parts[4]

            # Update SpO₂ if valid int
            if spo2_str.isdigit():
                spo2 = int(spo2_str)
                update_sensor("spo2", spo2)

            # Update BPM if valid int
            if bpm_str.isdigit():
                bpm = int(bpm_str)
                update_sensor("bpm", bpm)

            # Update perfusion index if valid float
            try:
                perf = float(pa_str)
                update_sensor("perfusion", perf)
            except ValueError:
                # ignore non-numeric perfusion
                pass

            # Sleep a bit (adjust to your device’s data rate)
            time.sleep(1)

        except serial.SerialException as e:
            # Likely device unplugged
            print(f"[serial_reader] SerialException: {e}. Reconnecting…")
            set_serial_mode(False)
            try:
                ser.close()
            except:
                pass
            ser = connect_serial()

        except Exception as e:
            # Unexpected error: log and keep going
            print(f"[serial_reader] Error: {e}")
            time.sleep(1)
