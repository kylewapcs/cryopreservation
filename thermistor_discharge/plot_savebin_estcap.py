import serial, struct, csv, time 
import numpy as np
import matplotlib.pyplot as plt

# ---- CONFIG ----
PORT        = 'COM9'
BAUDRATE    = 115200
TIMEOUT     = 5
N_SAMPLES   = 16384
BYTES_PER_ADC_ARRAY = N_SAMPLES * 2
BYTES_TIME  = 4
BYTES_ADC   = BYTES_PER_ADC_ARRAY * 2
TOTAL_BYTES = BYTES_ADC + BYTES_TIME
ADC_MAX     = 1023.0
V_REF       = 3.3
R_OHMS      = 1000000  # 1 MΩ
CONFIRM_SAMPLES = 5
CSV_OUT     = r'C:\Users\klipk\Downloads\capacitorheatedup50.csv'

def get_teensy_data():
    with serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT) as ser:
        ser.setDTR(True)
        time.sleep(2.5)
        ser.reset_input_buffer()
        ser.write(b'S')
        time.sleep(0.05)

        raw = ser.read(TOTAL_BYTES)
        if len(raw) != TOTAL_BYTES:
            raise RuntimeError(f'Got {len(raw)} / {TOTAL_BYTES} bytes')
        
        with open(r'C:\Users\klipk\Downloads\capacitorheatedup50_raw.bin', 'wb') as bin_file:
            bin_file.write(raw)
        

        cap_adc_data    = raw[:BYTES_PER_ADC_ARRAY]
        therm_adc_data  = raw[BYTES_PER_ADC_ARRAY:2 * BYTES_PER_ADC_ARRAY]
        time_data       = raw[2 * BYTES_PER_ADC_ARRAY:]

        cap_readings    = struct.unpack('<' + 'H' * N_SAMPLES, cap_adc_data)
        therm_readings  = struct.unpack('<' + 'H' * N_SAMPLES, therm_adc_data)
        total_time_us   = struct.unpack('<I', time_data)[0]

    return cap_readings, therm_readings, total_time_us


cap_readings, therm_readings, total_time_us = get_teensy_data()
voltages = np.array(cap_readings) / ADC_MAX * V_REF
voltage_therm = np.array(therm_readings) / ADC_MAX * V_REF
therm_readings = ((325 - 100 * voltage_therm) / ( 100 * voltage_therm) - 1) / (-3.9083e-3)
times = np.linspace(0, total_time_us, N_SAMPLES)


# Save to CSV
with open(CSV_OUT, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['index', 'time_us', 'voltage', 'temperature'])
    for i in range(N_SAMPLES):
        writer.writerow([i, times[i], voltages[i], therm_readings[i]])

start = CONFIRM_SAMPLES
N_fit = 16384 # samples to include in fit


t_fit = times[start:start+N_fit] * 1e-6  # us → seconds
v_fit = np.clip(voltages[start:start+N_fit], 1e-6, None)  # avoid log(0)

y = np.log(v_fit)
m, b = np.polyfit(t_fit, y, 1)

C_estimated_pF = -1 / (m * R_OHMS) * 1e12  
tau_fit_us = -1 / m * 1e6  
V0_fit = np.exp(b)  

print(f"Estimated Capacitance: {C_estimated_pF:.2f} pF")
print(f"Temperature: {therm_readings[0]} -> {therm_readings[8191]}")

plt.figure(figsize=(10, 6))
plt.plot(times, voltages, label='Measured Voltage')
plt.plot(t_fit * 1e6, np.exp(m * t_fit + b), '--', label='Log Fit', linewidth=2)  
plt.axvline(times[CONFIRM_SAMPLES], color='gray', linestyle=':', label='Decay Start')
plt.xlabel('Time (us)')
plt.ylabel('Voltage (V)')
#plt.yscale('log')
#plt.title('Capacitor Discharge (Log-Linear Fit)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show(block=True)