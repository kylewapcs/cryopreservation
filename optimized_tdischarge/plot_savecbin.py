import serial
import struct
import time
import os

import numpy as np
import matplotlib.pyplot as plt

# ---- CONFIG ----
PORT      = 'COM9'
BAUDRATE  = 115200
TIMEOUT   = 5

V_REF     = 3.3
ADC_MAX   = 1023.0
R_REF     = 1000.0  # series resistor in Ω

S_HIGH    = 16000
S_LOW     = 16000
BYTES_H   = S_HIGH * 2
BYTES_TH  = 4
BYTES_L   = S_LOW  * 2
BYTES_TL  = 4
BYTES_AG  = 2
TOTAL_BYTES = BYTES_H + BYTES_TH + BYTES_L + BYTES_TL + BYTES_AG

# Directory to save raw dumps
RAW_DIR = r'C:\Users\klipk\Downloads\teensy_raw'
os.makedirs(RAW_DIR, exist_ok=True)

def pt1000_lookup(R):
    T_ref = np.array([-79, -70, -60, -50, -40, -30,
                      -20, -10,   0,  10,  20,  30])
    R_ref = np.array([687.30, 723.30, 763.30, 803.10,
                      842.70, 882.20, 921.60, 960.90,
                      1000.00,1039.00,1077.90,1116.70])
    return np.interp(R, R_ref, T_ref)

def get_teensy_data():
    with serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT) as ser:
        ser.setDTR(True)
        time.sleep(2.0)
        ser.reset_input_buffer()

        ser.write(b'S')
        time.sleep(0.05)

        raw = ser.read(TOTAL_BYTES)
        if len(raw) != TOTAL_BYTES:
            raise RuntimeError(f"Expected {TOTAL_BYTES} bytes, got {len(raw)}")

    # save raw packet to timestamped file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    fname = os.path.join(RAW_DIR, f"teensy_raw_{timestamp}.bin")
    with open(fname, 'wb') as f:
        f.write(raw)
    print(f"[OK] Raw data saved to {fname}")

    # now parse it
    idx = 0
    vh        = np.frombuffer(raw[idx:idx+BYTES_H], dtype=np.uint16); idx += BYTES_H
    t_high    = struct.unpack('<I', raw[idx:idx+4])[0]; idx += 4
    vl        = np.frombuffer(raw[idx:idx+BYTES_L], dtype=np.uint16); idx += BYTES_L
    t_low     = struct.unpack('<I', raw[idx:idx+4])[0]; idx += 4
    avg_count = struct.unpack('<H', raw[idx:idx+2])[0]

    return vh, t_high, vl, t_low, avg_count

if __name__ == "__main__":
    vh, t_high, vl, t_low, avg_count = get_teensy_data()

    # build time axes (in microseconds)
    dt_high     = t_high / S_HIGH
    dt_low      = t_low  / S_LOW
    t_high_axis = np.arange(S_HIGH) * dt_high
    t_low_axis  = t_high_axis[-1] + dt_high + np.arange(S_LOW) * dt_low

    # convert counts → volts
    v_high = vh * (V_REF / ADC_MAX)
    v_low  = vl * (V_REF / ADC_MAX)

    # compute temperature
    V_th   = avg_count / ADC_MAX * V_REF
    R_th   = R_REF * V_th / (V_REF - V_th)
    T_degC = pt1000_lookup(R_th)

    # print sampling intervals & temperature
    print(f"High-speed: avg {dt_high:.2f} µs/sample")
    print(f"Low-speed : avg {dt_low:.2f} µs/sample")
    print(f"Measured Temperature: {T_degC:.1f} °C")

    # plot
    plt.figure(figsize=(10,6))
    plt.plot(t_high_axis, v_high, label="High-speed")
    plt.plot(t_low_axis,  v_low,  label="Low-speed")
    plt.xlabel("Time (µs)")
    plt.ylabel("Voltage (V)")
    plt.title(f"Decay Curve @ {T_degC:.1f} °C")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
