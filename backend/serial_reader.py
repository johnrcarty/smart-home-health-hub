import os
import time
import serial
from serial.tools import list_ports
from dotenv import load_dotenv

from state_manager import update_sensor, set_serial_mode, broadcast_serial_raw

load_dotenv()

# Default Baud Rate (can override with .env)
BAUD_RATE = int(os.getenv("BAUD_RATE", 19200))

try:
    # Try to get baud_rate from DB settings if available without importing DB here
    from crud.settings import get_setting
    from db import get_db
    def get_baud_rate():
        try:
            db = next(get_db())
            val = get_setting(db, "baud_rate", BAUD_RATE)
            db.close()
            try:
                return int(val)
            except Exception:
                return BAUD_RATE
        except Exception:
            return BAUD_RATE
except Exception:
    def get_baud_rate():
        return BAUD_RATE

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
                ser = serial.Serial(port, get_baud_rate(), timeout=1, rtscts=False, dsrdtr=False)
                print(f"[serial_reader] Connected to {port} @ {ser.baudrate} baud")
                set_serial_mode(True)
                return ser
            except Exception as e:
                print(f"[serial_reader] Failed to open {port}: {e}")

        set_serial_mode(False)
        print("[serial_reader] Retrying in 5s…")
        time.sleep(5)


def serial_loop():
    ser = connect_serial()

    last_baud_check = time.time()
    check_interval = 2.0  # seconds

    while True:
        try:
            # Periodically check if baud rate setting has changed
            now = time.time()
            if now - last_baud_check >= check_interval:
                try:
                    desired_baud = int(get_baud_rate())
                    if desired_baud != ser.baudrate:
                        print(f"[serial_reader] Baud rate changed from {ser.baudrate} to {desired_baud}. Reconnecting…")
                        try:
                            ser.close()
                        except Exception:
                            pass
                        ser = connect_serial()
                except Exception as e:
                    print(f"[serial_reader] Error checking/updating baud rate: {e}")
                finally:
                    last_baud_check = now

            raw = ser.readline().decode("ascii", errors="ignore").strip()
            if not raw:
                continue

            # broadcast raw line for preview
            try:
                broadcast_serial_raw(raw)
            except Exception:
                pass

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
