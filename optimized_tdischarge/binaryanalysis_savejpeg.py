# 2) File-based analysis of one dump
import os
import struct

import numpy as np
import matplotlib.pyplot as plt

# ---- CONFIG ----
FILE_PATH = r'C:\Users\klipk\Downloads\raw_heatdata_logs\teensy_raw_1.bin'

V_REF   = 3.3
ADC_MAX = 1023.0
R_REF   = 1000.0  # Ω

S_HIGH  = 16000
S_LOW   = 16000
BYTES_H = S_HIGH * 2
BYTES_TH= 4
BYTES_L = S_LOW  * 2
BYTES_TL= 4
BYTES_AG= 4             # float32 at end
TOTAL   = BYTES_H + BYTES_TH + BYTES_L + BYTES_TL + BYTES_AG

def pt1000_lookup(R):
    T_ref = np.array([-79, -70, -60, -50, -40, -30,
                      -20, -10,   0,  10,  20,  30])
    R_ref = np.array([687.30, 723.30, 763.30, 803.10,
                      842.70, 882.20, 921.60, 960.90,
                      1000.00,1039.00,1077.90,1116.70])
    return np.interp(R, R_ref, T_ref)

if not os.path.isfile(FILE_PATH):
    raise FileNotFoundError(f"No such file: {FILE_PATH}")

with open(FILE_PATH, 'rb') as f:
    raw = f.read()
if len(raw) != TOTAL:
    raise ValueError(f"Expected {TOTAL} bytes, got {len(raw)}")

idx     = 0
vh      = np.frombuffer(raw[idx:idx+BYTES_H], dtype=np.uint16); idx += BYTES_H
t_high  = struct.unpack('<I', raw[idx:idx+BYTES_TH])[0];          idx += BYTES_TH
vl      = np.frombuffer(raw[idx:idx+BYTES_L], dtype=np.uint16); idx += BYTES_L
t_low   = struct.unpack('<I', raw[idx:idx+BYTES_TL])[0]

# unpack float32 thermistor mean
avg_ct  = struct.unpack('<f', raw[-BYTES_AG:])[0]

# time axes
dt_high = t_high / S_HIGH
dt_low  = t_low  / S_LOW
th_ax   = np.arange(S_HIGH) * dt_high
tl_ax   = th_ax[-1] + dt_high + np.arange(S_LOW) * dt_low

# voltages
v_high  = vh * (V_REF / ADC_MAX)
v_low   = vl * (V_REF / ADC_MAX)

# temperature
v_th    = avg_ct / ADC_MAX * V_REF
R_th    = R_REF * v_th / (V_REF - v_th)
T_deg   = pt1000_lookup(R_th)

def calculate_capacitance(t_us, v, R_ohm):
    t = t_us * 1e-6   # now in seconds

    # limit fit to the “clean” exponential region:
    # here I pick v > 5% of V0 to avoid floor/noise
    v0 = v[0]
    mask = (v > 0.05*v0) & (v < v0)
    t_fit = t[mask]
    v_fit = v[mask]

    # linearize: ln(V/V0) = -t/(R C)
    ln_ratio = np.log(v_fit / v0)

    # slope = d/dt [ln(V/V0)] = -1/(R C)
    slope, intercept = np.polyfit(t_fit, ln_ratio, 1)
    tau_s = -1.0 / slope       # in seconds
    C_F   = tau_s / R_ohm * 1e12     # in farads

    # return both in familiar units
    return float(C_F)     # tau back to microseconds

t_all = np.concatenate((th_ax, tl_ax))
v_all = np.concatenate((v_high, v_low))
print(calculate_capacitance(t_all, v_all, 1000000))
print(T_deg)

plt.figure(figsize=(10,6))
plt.plot(th_ax, v_high, label="High-speed")
plt.plot(tl_ax, v_low,  label="Low-speed")
plt.xlabel("Time (µs)")
plt.ylabel("Voltage (V)")
plt.title(f"Decay Curve @ {T_deg:.1f}°C")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
