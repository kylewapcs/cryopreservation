import serial
import struct
import time
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
S_LOW1 = 1200
S_LOW       = 16000

BYTES_H     = S_HIGH * 2
BYTES_TH    = 4
BYTES_L     = S_LOW * 2
BYTES_TL1   = 4  # totalLow1
BYTES_TL2   = 4  # totalLow2 (totalLow)
BYTES_AG    = 4  # avgTherm (float32)

TOTAL_BYTES = BYTES_H + BYTES_TH + BYTES_L + BYTES_TL1 + BYTES_TL2 + BYTES_AG

def pt1000_lookup(R):
    T_ref = np.array([-79, -70, -60, -50, -40, -30,
                      -20, -10, 0, 10, 20, 30])
    R_ref = np.array([687.30, 723.30, 763.30, 803.10,
                      842.70, 882.20, 921.60, 960.90,
                      1000.00, 1039.00, 1077.90, 1116.70])
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
    avg_count = struct.unpack('<f', raw[idx:idx+BYTES_AG])[0]

    return vh, t_high, vl, totalLow1, totalLow, avg_count

if __name__ == "__main__":
    vh, t_high, vl, totalLow1, totalLow, avg_count = get_teensy_data()

    # Calculate time per sample for high-speed
    dt_h = t_high / S_HIGH  # microseconds per sample

    # For low-speed: split into two phases
    # Phase 1: first 150 samples
    dt_l1 = totalLow1 / S_LOW1

    # Phase 2: remaining samples
    dt_l2 = (totalLow - totalLow1) / (S_LOW - 1200)

    # Build time arrays (microseconds)
    t_h = np.arange(S_HIGH) * dt_h + dt_h

    t_l1 = t_h[-1] + dt_h + np.arange(1200) * dt_l1 + dt_l1
    t_l2 = t_l1[-1] + dt_l1 + np.arange(S_LOW - 1200) * dt_l2 + dt_l2

    t_l = np.concatenate((t_l1, t_l2))

    # Convert ADC values to voltages
    v_h = vh * (V_REF / ADC_MAX_10)        # high-speed 10-bit ADC
    v_l = vl * (V_REF / ADC_MAX_12)        # low-speed 12-bit ADC

    # Normalize signals by first high-speed sample (assumed stable voltage)
    normal = v_h[0]
    v_h = v_h / 3.3
    v_l = v_l / 3.3

    # Calculate temperature from thermistor voltage
    V_th = avg_count / ADC_MAX_10 * V_REF
    R_th = R_REF * V_th / (V_REF - V_th)
    T_C = pt1000_lookup(R_th)

    # Function to calculate capacitance from RC decay fit
    def calculate_capacitance(t_us, v, R_ohm):
        t = t_us * 1e-6  # convert us to seconds

        v0 = v[0]
        mask = (v > 0.05 * v0) & (v < v0)
        t_fit = t[mask]
        v_fit = v[mask]

        ln_ratio = np.log(v_fit / v0)
        slope, _ = np.polyfit(t_fit, ln_ratio, 1)
        tau_s = -1.0 / slope  # seconds
        C_F = tau_s / R_ohm * 1e12  # Farads to pF

        return float(C_F)

    t_all = np.concatenate((t_h, t_l))
    v_all = np.concatenate((v_h, v_l))

    print(f'Capacitance (pF): {calculate_capacitance(t_h[:100], v_h[:100], 1000000)}')
    print(f"High-speed sample interval: {dt_h:.2f} µs/sample")
    print(f"Low-speed phase 1 sample interval: {dt_l1:.2f} µs/sample")
    print(f"Low-speed phase 2 sample interval: {dt_l2:.2f} µs/sample")
    print(f"Temperature: {T_C:.1f} °C")

    plt.figure(figsize=(10,6))
    plt.plot(t_h, v_h, label="High-speed")
    plt.plot(t_l1, v_l[:1200], label="Low-speed phase 1 (no averaging)")
    plt.plot(t_l2, v_l[1200:], label="Low-speed phase 2 (averaged)")
    plt.xlabel("Time (µs)")
    plt.ylabel("Normalized Voltage (V/V0)")
    plt.title(f"Decay Curve @ {T_C:.1f}°C")
    plt.xlim(1, 100)
    plt.yscale('log')
    plt.xscale('linear')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
