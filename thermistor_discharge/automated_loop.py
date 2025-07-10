import serial
import time
import os
import numpy as np
import struct

PORT = 'COM9'
BAUDRATE = 115200
TIMEOUT = 5
N_SAMPLES = 8192
BYTES_PER_ADC_ARRAY = N_SAMPLES * 2
BYTES_TIME = 4
BYTES_ADC = BYTES_PER_ADC_ARRAY * 2
TOTAL_BYTES = BYTES_ADC + BYTES_TIME
OUTPUT_DIR = r'C:\Users\klipk\Downloads\raw_heatdata_logs'

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_next_indexed_filename(base='raw_binary', ext='bin'):
    i = 1
    while True:
        path = os.path.join(OUTPUT_DIR, f"{base}{i}.{ext}")
        if not os.path.exists(path):
            return path, i
        i += 1

def get_teensy_raw(ser):
    ser.write(b'S')              # Trigger Teensy to start sampling
    time.sleep(0.05)             # Let it process the command
    raw = ser.read(TOTAL_BYTES)  # Read full data packet
    if len(raw) != TOTAL_BYTES:
        print(f"[!] Incomplete packet: {len(raw)} / {TOTAL_BYTES} bytes")
        return None
    return raw

def pt1000_lookup(R):
    """Convert resistance to temperature using PT1000 lookup table"""
    T_ref = [-79, -70, -60, -50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    R_ref = [687.30, 723.30, 763.30, 803.10, 842.70, 882.20, 921.60,
             960.90, 1000.00, 1039.00, 1077.90, 1116.70, 1155.40, 1193.60,
             1232.40, 1271.00, 1309.50, 1347.80, 1385.90]
    return round(np.interp(R, R_ref, T_ref), 1)

def get_teensy_binary_data(fp):     
    raw = fp.read()

    therm_adc_data  = raw[BYTES_PER_ADC_ARRAY:2 * BYTES_PER_ADC_ARRAY]
    therm_readings  = struct.unpack('<' + 'H' * N_SAMPLES, therm_adc_data)

    ADC_MAX     = 1023.0
    V_REF       = 3.25
    R_OHMS      = 1000000  # 1 MΩ
    CONFIRM_SAMPLES = 5
    R_REF = 1000.0       # Reference resistor in ohms
    # process the data 
    therm_readings1 = np.average(therm_readings)
    voltage_therm = therm_readings1 * V_REF / ADC_MAX
    R_therm = R_REF*voltage_therm/(V_REF-voltage_therm)
    T_therm = pt1000_lookup(R_therm)
    x = T_therm
    return x


def loop_log_raw_data():
    print("Logging loop started. Press Ctrl+C to stop.")
    with serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT) as ser:
        ser.setDTR(False)  # ← Don't reset Teensy
        time.sleep(1.0)    # Let Teensy fully boot just once
        while True:
            raw = get_teensy_raw(ser)
            if raw:
                path, idx = get_next_indexed_filename()
                with open(path, 'wb') as f:
                    f.write(raw)
                with open(path, 'rb') as f:
                    temperature = get_teensy_binary_data(f)
                print(f"[OK] Saved to {path} ({len(raw)} bytes): {temperature} degrees C")
            else:
                print("[X] Skipped due to bad packet.")
            time.sleep(0.5)

if __name__ == '__main__':
    try:
        loop_log_raw_data()
    except KeyboardInterrupt:
        print("\n[OK] Logging stopped by user.")
