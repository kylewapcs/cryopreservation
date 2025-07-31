import serial
import struct
import time
import os
import numpy as np
import matplotlib.pyplot as plt

# ---- CONFIG ----
PORT        = 'COM9'
BAUDRATE    = 115200
TIMEOUT     = 5

V_REF       = 3.3
ADC_MAX_10  = 1023.0
ADC_MAX_12  = 4095.0
R_REF       = 1000.0

S_HIGH      = 50
S_LOW       = 16000

BYTES_H     = S_HIGH * 2
BYTES_TH    = 4
BYTES_L     = S_LOW * 2
BYTES_TL1   = 4
BYTES_TL2   = 4
BYTES_AG    = 4

TOTAL_BYTES = BYTES_H + BYTES_TH + BYTES_L + BYTES_TL1 + BYTES_TL2 + BYTES_AG

RAW_DIR = r'C:\Users\klipk\Downloads\test6_logs'
os.makedirs(RAW_DIR, exist_ok=True)

def pt1000_lookup(R):
    T_ref = np.array([-79, -70, -60, -50, -40, -30,
                      -20, -10, 0, 10, 20, 30])
    R_ref = np.array([687.30, 723.30, 763.30, 803.10,
                      842.70, 882.20, 921.60, 960.90,
                      1000.00, 1039.00, 1077.90, 1116.70])
    return np.interp(R, R_ref, T_ref)

def get_teensy_raw(ser):
    ser.write(b'S')
    time.sleep(0.05)
    buf = ser.read(TOTAL_BYTES)
    return buf if len(buf) == TOTAL_BYTES else None

def parse_packet(raw):
    idx = 0
    vh = np.frombuffer(raw[idx:idx+BYTES_H], dtype=np.uint16)
    idx += BYTES_H
    t_high = struct.unpack('<I', raw[idx:idx+BYTES_TH])[0]
    idx += BYTES_TH
    vl = np.frombuffer(raw[idx:idx+BYTES_L], dtype=np.uint16)
    idx += BYTES_L
    totalLow1 = struct.unpack('<I', raw[idx:idx+BYTES_TL1])[0]
    idx += BYTES_TL1
    totalLow = struct.unpack('<I', raw[idx:idx+BYTES_TL2])[0]
    idx += BYTES_TL2
    avgTherm = struct.unpack('<f', raw[idx:idx+BYTES_AG])[0]
    return vh, t_high, vl, totalLow1, totalLow, avgTherm

def compute_temperature(avg_count):
    V_th = avg_count / ADC_MAX_10 * V_REF
    R_th = R_REF * V_th / (V_REF - V_th) if V_th != 0 else 0
    return pt1000_lookup(R_th) if R_th > 0 else None

def next_filename(base="teensy_raw", ext="bin"):
    i = 1
    while True:
        fname = f"{base}_{i}.{ext}"
        path = os.path.join(RAW_DIR, fname)
        if not os.path.exists(path):
            return path, fname
        i += 1

def loop_log_raw_data():
    print("=== Logging loop started; Ctrl+C to stop ===")
    with serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT) as ser:
        ser.setDTR(False)
        time.sleep(1)
        ser.reset_input_buffer()

        plt.ion()
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.set_xlabel("Time (µs)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title("Live Dielectric Decay Curves (Log-Log Scale)")

        count = 1
        lines = []   # List to keep plotted lines
        labels = []  # Corresponding labels

        runs_to_average = 10
        voltage_accum = None
        temperature_accum = []
        run_buffer = 0

        while True:
            raw = get_teensy_raw(ser)
            if raw:
                path, fname = next_filename()
                with open(path, 'wb') as f:
                    f.write(raw)

                vh, t_high, vl, totalLow1, totalLow, avgTherm = parse_packet(raw)
                T = compute_temperature(avgTherm)

                # Calculate per-sample time intervals
                dt_high = t_high / S_HIGH
                dt_low1 = totalLow1 / 1200          # First 1200 low-speed samples
                dt_low2 = (totalLow) / (S_LOW - 1200)  # Remaining samples

                # Build time axes
                t_h = np.arange(S_HIGH) * dt_high
                t_l1 = t_h[-1] + dt_high + np.arange(1200) * dt_low1
                t_l2 = t_l1[-1] + dt_low1 + np.arange(S_LOW - 1200) * dt_low2
                t_all = np.concatenate((t_h, t_l1, t_l2))

                # Convert ADC counts to voltages WITHOUT normalization
                v_h = vh * (V_REF / ADC_MAX_10)
                v_l1 = vl[:1200] * (V_REF / ADC_MAX_12)
                v_l2 = vl[1200:] * (V_REF / ADC_MAX_12)
                v_all = np.concatenate((v_h, v_l1, v_l2))

                # Clip to avoid zero or negative values on log scale
                t_all_clipped = np.clip(t_all, 1e-3, None)
                v_all_clipped = np.clip(v_all, 1e-6, None)

                # Accumulate for averaging
                if voltage_accum is None:
                    voltage_accum = np.zeros_like(v_all_clipped)
                voltage_accum += v_all_clipped
                temperature_accum.append(T if T else np.nan)
                run_buffer += 1

                if run_buffer == runs_to_average:
                    voltage_avg = voltage_accum / runs_to_average
                    temperature_avg = np.nanmean(temperature_accum)

                    label = f"Avg of {runs_to_average} runs @ {temperature_avg:.1f}°C" if not np.isnan(temperature_avg) else f"Avg of {runs_to_average} runs @ Unknown T"
                    line, = ax.plot(t_all_clipped, voltage_avg, label=label)

                    lines.append(line)
                    labels.append(label)

                    if len(lines) > 10:
                        labels.pop(0)
                        lines.pop(0)

                    ax.legend(lines, labels, loc='upper right', fontsize='small')
                    ax.set_xscale('log')
                    ax.set_yscale('log')
                    plt.xlim(10, 1000)
                    plt.ylim(0.01, 5)
                    plt.draw()
                    plt.pause(0.1)

                    print(f"[{count:03d}] Saved {fname} | Avg Temp: {temperature_avg if not np.isnan(temperature_avg) else 'N/A'} °C | "
                          f"HS dt: {dt_high:.2f} us/sample | LS dt1: {dt_low1:.2f} us/sample | LS dt2: {dt_low2:.2f} us/sample")

                    count += 1
                    voltage_accum = None
                    temperature_accum = []
                    run_buffer = 0

            else:
                print("[X] Skipped bad packet")

            time.sleep(0.5)

if __name__ == '__main__':
    try:
        loop_log_raw_data()
    except KeyboardInterrupt:
        print("\n=== Logging stopped by user ===")
