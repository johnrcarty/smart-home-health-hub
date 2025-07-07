import os
import time
import serial
from serial.tools import list_ports
from dotenv import load_dotenv

from state_manager import update_sensor, set_serial_mode

load_dotenv()

# Default Baud Rate (can override with .env)
BAUD_RATE = int(os.getenv("BAUD_RATE", 19200))

def find_serial_port():
    """
    Scan connected serial ports for a known USB-Serial device.
    Returns the device path or None if not found.
    """
    ports = list_ports.comports()
    for port in ports:
        desc = port.description.lower()
        if "cp210" in desc or "uart" in desc:
            print(f"[serial_reader] Found serial device: {port.device} ({desc})")
            return port.device

    print("[serial_reader] No compatible serial device found.")
    return None


def connect_serial():
    """
    Attempt to find and open the serial port. Retry every 5s if needed.
    """
    while True:
        port = find_serial_port()
        if port:
            try:
                ser = serial.Serial(port, BAUD_RATE, timeout=1, rtscts=False, dsrdtr=False)
                print(f"[serial_reader] Connected to {port} @ {BAUD_RATE} baud")
                set_serial_mode(True)
                return ser
            except Exception as e:
                print(f"[serial_reader] Failed to open {port}: {e}")

        set_serial_mode(False)
        print("[serial_reader] Retrying in 5s…")
        time.sleep(5)


def serial_loop():
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

            timestamp = f"{parts[0]} {parts[1]}"
            spo2_str = parts[2].rstrip("*")
            bpm_str = parts[3].rstrip("*")
            pa_str = parts[4]
            status = parts[5] if len(parts) > 5 else None

            updates = []

            if spo2_str.isdigit():
                updates.append(("spo2", int(spo2_str)))

            if bpm_str.isdigit():
                updates.append(("bpm", int(bpm_str)))

            try:
                perf = float(pa_str)
                updates.append(("perfusion", perf))
            except ValueError:
                pass

            if status:
                updates.append(("status", status))

            if updates:
                # Debug the updates being sent
                print(f"[serial_reader] Sending updates: {updates}")
                
                # Send the updates as a tuple rather than a list
                # Lists aren't hashable but tuples are
                update_sensor(tuple(updates), 'raw_data', raw)

            print(f"[serial_reader] {timestamp} SpO2: {spo2_str}, BPM: {bpm_str}, Perfusion: {pa_str}, Status: {status}")

        except serial.SerialException:
            print("[serial_reader] SerialException. Reconnecting…")
            set_serial_mode(False)
            try:
                ser.close()
            except:
                pass
            ser = connect_serial()

        except Exception as e:
            print(f"[serial_reader] Error: {e}")
            time.sleep(1)
