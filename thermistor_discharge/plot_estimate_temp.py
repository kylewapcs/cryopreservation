import numpy as np
import matplotlib.pyplot as plt
import serial
import struct
import time

# --- CONFIG ---
PORT = 'COM9'
BAUDRATE = 115200
TIMEOUT = 5
N_SAMPLES = 16384
BYTES_ADC0 = N_SAMPLES * 2
BYTES_ADC1 = N_SAMPLES * 2
BYTES_TIME = 4
TOTAL_BYTES = BYTES_ADC0 + BYTES_ADC1 + BYTES_TIME

V_REF = 3.3
ADC_BITS = 10
ADC_SCALE = V_REF / (2 ** ADC_BITS)

def pt1000_lookup(R):
    T_ref = [-79, -70, -60, -50, -40, -30, -20, -10, 0, 10, 20, 30]
    R_ref = [687.30, 723.30, 763.30, 803.10, 842.70, 882.20, 921.60,
             960.90, 1000.00, 1039.00, 1077.90, 1116.70]
    return np.interp(R, R_ref, T_ref)

def get_teensy_measurement():
    with serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT) as ser:
        ser.setDTR(False)
        ser.flushInput()
        time.sleep(1.0)  # Allow Teensy to finish booting

        ser.write(b'S')  # Trigger Teensy sampling
        time.sleep(0.1)  # Give it time to collect and send

        raw = bytearray()
        while len(raw) < TOTAL_BYTES:
            packet = ser.read(TOTAL_BYTES - len(raw))
            if not packet:
                break
            raw.extend(packet)

    if len(raw) != TOTAL_BYTES:
        print(f"[!] Incomplete packet: {len(raw)} / {TOTAL_BYTES} bytes received")
        return None
    return raw

# --- RUN ---
raw = get_teensy_measurement()
if raw is None:
    exit()

adc0 = np.frombuffer(raw[0:BYTES_ADC0], dtype=np.uint16)
adc1 = np.frombuffer(raw[BYTES_ADC0:BYTES_ADC0 + BYTES_ADC1], dtype=np.uint16)
total_time_us = struct.unpack('<I', raw[-4:])[0]

voltages = adc0 * ADC_SCALE
therm_voltages = adc1 * ADC_SCALE
times = np.linspace(0, total_time_us, N_SAMPLES)

# --- Calculate Temperature ---
therm_half = therm_voltages[N_SAMPLES // 2:]
therm_avg = np.mean(therm_half)

if 0.05 < therm_avg < (V_REF - 0.05):
    R_thermistor = 1000 * therm_avg / (V_REF - therm_avg)
    T_avg = round(pt1000_lookup(R_thermistor), 1)
    print(f"[INFO] Thermistor average voltage: {therm_avg:.4f} V")
    print(f"[INFO] Estimated temperature: {T_avg}°C")
else:
    T_avg = None
    print("[INFO] Invalid thermistor voltage, skipping temperature estimation.")

# --- PLOT ---
label = f"{T_avg}°C" if T_avg is not None else "Unknown T"

plt.figure(figsize=(12, 7))
plt.plot(times, voltages, label=label)
plt.xlabel("Time (µs)")
plt.ylabel("Voltage (V)")
plt.title("Voltage vs Time from Live Measurement")
plt.grid(True)
plt.legend(title="Temperature")
plt.ylim(0, 3.3)
plt.tight_layout()
plt.show()
