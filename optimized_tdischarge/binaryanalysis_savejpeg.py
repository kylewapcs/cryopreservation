import os
import struct
import numpy as np
import matplotlib.pyplot as plt

# ---- CONFIG ----
FILE_PATH = r'C:\Users\klipk\Downloads\test7_logs\teensy_raw_5.bin'

V_REF   = 3.3
ADC_MAX_10 = 1023.0
R_REF   = 1000.0  # Ω

S_HIGH  = 50       # Update to your actual S_HIGH
S_LOW   = 16000    # Your S_LOW

BYTES_H = S_HIGH * 2
BYTES_TH = 4
BYTES_L = S_LOW * 2
BYTES_TL1 = 4
BYTES_TL2 = 4
BYTES_AG = 4       # float32 thermistor avg at end

TOTAL = BYTES_H + BYTES_TH + BYTES_L + BYTES_TL1 + BYTES_TL2 + BYTES_AG

def pt1000_lookup(R):
    T_ref = np.array([-79, -70, -60, -50, -40, -30,
                      -20, -10, 0, 10, 20, 30])
    R_ref = np.array([687.30, 723.30, 763.30, 803.10,
                      842.70, 882.20, 921.60, 960.90,
                      1000.00, 1039.00, 1077.90, 1116.70])
    return np.interp(R, R_ref, T_ref)

if not os.path.isfile(FILE_PATH):
    raise FileNotFoundError(f"No such file: {FILE_PATH}")

with open(FILE_PATH, 'rb') as f:
    raw = f.read()
if len(raw) != TOTAL:
    raise ValueError(f"Expected {TOTAL} bytes, got {len(raw)}")

idx = 0
vh = np.frombuffer(raw[idx:idx+BYTES_H], dtype=np.uint16)
idx += BYTES_H

t_high = struct.unpack('<I', raw[idx:idx+BYTES_TH])[0]
idx += BYTES_TH

vl = np.frombuffer(raw[idx:idx+BYTES_L], dtype=np.uint16)
idx += BYTES_L

totalLow1 = struct.unpack('<I', raw[idx:idx+BYTES_TL1])[0]
idx += BYTES_TL1

totalLow2 = struct.unpack('<I', raw[idx:idx+BYTES_TL2])[0]
idx += BYTES_TL2

avg_ct = struct.unpack('<f', raw[idx:idx+BYTES_AG])[0]

# Calculate time axes:
dt_high = t_high / S_HIGH
dt_low1 = totalLow1 / 1200.0         # first 1200 low-speed samples
dt_low2 = (totalLow2 - totalLow1) / (S_LOW - 1200.0)  # remaining samples

th_ax = np.arange(S_HIGH) * dt_high
tl_ax1 = th_ax[-1] + dt_high + np.arange(1200) * dt_low1

tl_ax2 = tl_ax1[-1] + dt_low1 + np.arange(S_LOW - 1200) * dt_low2

# Voltages
v_high = vh * (V_REF / ADC_MAX_10)
v_low1 = vl[:1200] * (V_REF / 4095.0)    # 12-bit ADC max assumed
v_low2 = vl[1200:] * (V_REF / 4095.0)

# Temperature calculation
v_th = avg_ct / ADC_MAX_10 * V_REF
R_th = R_REF * v_th / (V_REF - v_th)
T_deg = pt1000_lookup(R_th)

def calculate_capacitance(t_us, v, R_ohm):
    t = t_us * 1e-6  # convert to seconds
    v0 = v[0]
    mask = (v > 0.05 * v0) & (v < v0)
    t_fit = t[mask]
    v_fit = v[mask]
    ln_ratio = np.log(v_fit / v0)
    slope, _ = np.polyfit(t_fit, ln_ratio, 1)
    tau_s = -1.0 / slope
    C_f = tau_s / R_ohm * 1e12  # Farads to pF
    return float(C_f)

t_all = np.concatenate((th_ax, tl_ax1, tl_ax2))
v_all = np.concatenate((v_high, v_low1, v_low2))

capacitance_pf = calculate_capacitance(t_all, v_all, 1000000)
print(f"Estimated capacitance: {capacitance_pf:.2f} pF")
print(f"Temperature: {T_deg:.2f} °C")



plt.figure(figsize=(10, 6))
plt.plot(th_ax, v_high, label="High-speed")
plt.plot(tl_ax1, v_low1, label="Low-speed part 1")
plt.plot(tl_ax2, v_low2, label="Low-speed part 2")
plt.xlabel("Time (µs)")
plt.ylabel("Voltage (V)")
plt.xscale('linear')
plt.xlim(0, 50)
plt.ylim(0.01, 5)
plt.yscale('log')
plt.title(f"Decay Curve @ {T_deg:.1f} °C")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
