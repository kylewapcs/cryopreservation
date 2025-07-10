import numpy as np
import matplotlib.pyplot as plt
import os
import struct

# --- CONFIG ---
file_path = r"C:\Users\klipk\Downloads\capacitorheatedup50_raw.bin"  # Change if needed
N_SAMPLES = 16384
V_REF = 3.25
ADC_BITS = 10
ADC_SCALE = V_REF / (2 ** ADC_BITS)

def pt1000_lookup(R):
    T_ref = [-79, -70, -60, -50, -40, -30, -20, -10, 0, 10, 20, 30]
    R_ref = [687.30, 723.30, 763.30, 803.10, 842.70, 882.20, 921.60,
             960.90, 1000.00, 1039.00, 1077.90, 1116.70]
    return np.interp(R, R_ref, T_ref)

# --- READ AND DECODE ---
if not os.path.isfile(file_path):
    print(f"[!] File not found: {file_path}")
    exit()

with open(file_path, "rb") as f:
    raw = f.read()

expected_len = N_SAMPLES * 4 + 4
if len(raw) != expected_len:
    print(f"[!] File length mismatch: expected {expected_len}, got {len(raw)}")
    exit()

adc0 = np.frombuffer(raw[0:N_SAMPLES*2], dtype=np.uint16)
adc1 = np.frombuffer(raw[N_SAMPLES*2:N_SAMPLES*4], dtype=np.uint16)
total_time_us = struct.unpack("<I", raw[-4:])[0]
dt = total_time_us / N_SAMPLES

voltages = adc0 * ADC_SCALE
therm_voltages = adc1 * ADC_SCALE
times = np.arange(N_SAMPLES) * dt

# --- TEMPERATURE CALCULATION ---
if len(therm_voltages) > 6000:
    therm_segment = therm_voltages[6000:]
    R_vals = 1000 * therm_segment / (V_REF - therm_segment)
    T_vals = pt1000_lookup(R_vals)
    T_avg = round(np.mean(T_vals), 1)
else:
    T_avg = None

# --- PLOT ---
plt.figure(figsize=(12, 7))
label = f"{T_avg}°C" if T_avg is not None else "Unknown Temp"
plt.plot(times, voltages, label=label)
plt.xlabel("Time (µs)")
plt.ylabel("Voltage (V)")
plt.title("Voltage vs Time")
plt.grid(True)
plt.legend()
plt.xscale('log')  # Optional: comment out for linear time axis
plt.tight_layout()

# --- SHOW ---
plt.show()
