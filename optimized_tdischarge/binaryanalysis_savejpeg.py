import os
import struct

import numpy as np
import matplotlib.pyplot as plt

# ---- CONFIG ----
# Point this at the single file you want to analyze:
FILE_PATH = r'C:\Users\klipk\Downloads\raw_heatdata_logs\teensy_raw_1.bin'

V_REF   = 3.3
ADC_MAX = 1023.0
R_REF   = 1000.0  # series resistor in ohms

S_HIGH  = 16000
S_LOW   = 16000
BYTES_H = S_HIGH * 2        # high-speed buffer
BYTES_TH= 4                 # uint32 high-speed time
BYTES_L = S_LOW  * 2        # low-speed buffer
BYTES_TL= 4                 # uint32 low-speed time
BYTES_AG= 2                 # uint16 avg thermistor
TOTAL   = BYTES_H + BYTES_TH + BYTES_L + BYTES_TL + BYTES_AG

def pt1000_lookup(R):
    T_ref = np.array([-79, -70, -60, -50, -40, -30,
                      -20, -10,   0,  10,  20,  30])
    R_ref = np.array([687.30, 723.30, 763.30, 803.10,
                      842.70, 882.20, 921.60, 960.90,
                      1000.00,1039.00,1077.90,1116.70])
    return np.interp(R, R_ref, T_ref)

# --- READ RAW ---
if not os.path.isfile(FILE_PATH):
    raise FileNotFoundError(f"No such file: {FILE_PATH}")

with open(FILE_PATH, 'rb') as f:
    raw = f.read()

if len(raw) != TOTAL:
    raise ValueError(f"Expected {TOTAL} bytes, got {len(raw)}")

# --- PARSE ---
idx    = 0
vh     = np.frombuffer(raw[idx:idx+BYTES_H], dtype=np.uint16); idx += BYTES_H
t_high = struct.unpack('<I', raw[idx:idx+BYTES_TH])[0]       ; idx += BYTES_TH
vl     = np.frombuffer(raw[idx:idx+BYTES_L], dtype=np.uint16); idx += BYTES_L
t_low  = struct.unpack('<I', raw[idx:idx+BYTES_TL])[0]       # idx += BYTES_TL

# Grab the 16-bit thermistor average from the last 2 bytes:
avg_ct = struct.unpack('<H', raw[-BYTES_AG:])[0]

# --- TIME AXES ---
dt_high = t_high / S_HIGH
dt_low  = t_low  / S_LOW
th_axis = np.arange(S_HIGH) * dt_high
tl_axis = th_axis[-1] + dt_high + np.arange(S_LOW) * dt_low

# --- VOLTAGES ---
v_high = vh * (V_REF / ADC_MAX)
v_low  = vl * (V_REF / ADC_MAX)

# --- TEMPERATURE ---
v_th = avg_ct / ADC_MAX * V_REF
R_th = R_REF * v_th / (V_REF - v_th)
Tdeg = pt1000_lookup(R_th)

# --- PLOT ---
plt.figure(figsize=(10,6))
plt.plot(th_axis, v_high, label="High-speed")
plt.plot(tl_axis,  v_low,  label="Low-speed")
plt.xlabel("Time (µs)")
plt.ylabel("Voltage (V)")
plt.title(f"Decay Curve @ {Tdeg:.1f}°C")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
