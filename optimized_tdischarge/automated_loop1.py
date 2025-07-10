import serial
import struct
import time
import os

import numpy as np

# ---- CONFIG ----
PORT      = 'COM9'
BAUDRATE  = 115200
TIMEOUT   = 5

V_REF     = 3.3
ADC_MAX   = 1023.0
R_REF     = 1000.0  # Ω

S_HIGH    = 16000
S_LOW     = 16000
BYTES_H   = S_HIGH * 2
BYTES_TH  = 4
BYTES_L   = S_LOW  * 2
BYTES_TL  = 4
BYTES_AG  = 2
TOTAL_BYTES = BYTES_H + BYTES_TH + BYTES_L + BYTES_TL + BYTES_AG

RAW_DIR = r'C:\Users\klipk\Downloads\raw_heatdata_logs'
os.makedirs(RAW_DIR, exist_ok=True)

def pt1000_lookup(R):
    T_ref = np.array([-79, -70, -60, -50, -40, -30,
                      -20, -10,   0,  10,  20,  30])
    R_ref = np.array([687.30, 723.30, 763.30, 803.10,
                      842.70, 882.20, 921.60, 960.90,
                      1000.00,1039.00,1077.90,1116.70])
    return np.interp(R, R_ref, T_ref)

def get_teensy_raw(ser):
    ser.write(b'S')
    time.sleep(0.05)
    buf = ser.read(TOTAL_BYTES)
    return buf if len(buf)==TOTAL_BYTES else None

def parse_packet(raw):
    idx = 0
    vh     = np.frombuffer(raw[idx:idx+BYTES_H], dtype=np.uint16); idx += BYTES_H
    t_high = struct.unpack('<I', raw[idx:idx+4])[0];           idx += 4
    vl     = np.frombuffer(raw[idx:idx+BYTES_L], dtype=np.uint16); idx += BYTES_L
    t_low  = struct.unpack('<I', raw[idx:idx+BYTES_TL])[0]
    # always pull the true avg from the last two bytes
    avg_ct = struct.unpack('<H', raw[-BYTES_AG:])[0]
    return vh, t_high, vl, t_low, avg_ct

def compute_temperature(avg_count):
    V_th = avg_count / ADC_MAX * V_REF
    R_th = R_REF * V_th / (V_REF - V_th)
    return pt1000_lookup(R_th)

def next_filename(base="teensy_raw", ext="bin"):
    i = 1
    while True:
        f = f"{base}_{i}.{ext}"
        p = os.path.join(RAW_DIR, f)
        if not os.path.exists(p): return p, f
        i += 1

def loop_log_raw_data():
    print("=== Logging loop started; Ctrl+C to stop ===")
    with serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT) as ser:
        ser.setDTR(False)
        time.sleep(1)
        ser.reset_input_buffer()

        count = 1
        while True:
            raw = get_teensy_raw(ser)
            if raw:
                path, fname = next_filename()
                with open(path, 'wb') as f: f.write(raw)
                vh, t_high, vl, t_low, avg_ct = parse_packet(raw)
                T = compute_temperature(avg_ct)

                dt_high = t_high / S_HIGH
                dt_low  = t_low  / S_LOW

                print(f"[{count:03d}] Saved {fname} | "
                      f"T = {T:.1f} °C | "
                      f"HS rate ~ {dt_high:.2f} us/sample | "
                      f"LS rate ~ {dt_low:.2f} us/sample")
                count += 1
            else:
                print("[X] Skipped bad packet")
            time.sleep(0.5)

if __name__ == '__main__':
    try:
        loop_log_raw_data()
    except KeyboardInterrupt:
        print("\n=== Logging stopped by user ===")
