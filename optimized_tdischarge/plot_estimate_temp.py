import struct
import time

import numpy as np
import matplotlib.pyplot as plt
import serial

# — USER CONFIG —
PORT      = "COM9"
BAUDRATE  = 115200
V_REF     = 3.25
BITS      = 10
S_HIGH    = 16000
S_LOW     = 16000

ADC_SCALE = V_REF / (2**BITS - 1)
# sizes in bytes:
BYTES_HIGH = S_HIGH * 2
BYTES_TH   = 4
BYTES_LOW  = S_LOW  * 2
BYTES_TL   = 4
BYTES_AG   = 2
EXPECTED   = BYTES_HIGH + BYTES_TH + BYTES_LOW + BYTES_TL + BYTES_AG

def pt1000_lookup(R):
    T_ref = np.array([-79, -70, -60, -50, -40, -30,
                      -20, -10,   0,  10,  20,  30])
    R_ref = np.array([687.30, 723.30, 763.30, 803.10,
                      842.70, 882.20, 921.60, 960.90,
                      1000.00,1039.00,1077.90,1116.70])
    return np.interp(R, R_ref, T_ref)

def main():
    ser = serial.Serial(PORT, BAUDRATE, timeout=2)
    time.sleep(1)
    ser.reset_input_buffer()
    ser.write(b"S")

    buf = ser.read(EXPECTED)
    ser.close()
    if len(buf) != EXPECTED:
        print(f"Got {len(buf)} / {EXPECTED} bytes")
        return

    # parse the two voltage phases & times
    idx = 0
    vh = np.frombuffer(buf[idx:idx+BYTES_HIGH], dtype=np.uint16)
    idx += BYTES_HIGH

    th = struct.unpack("<I", buf[idx:idx+BYTES_TH])[0]
    idx += BYTES_TH

    vl = np.frombuffer(buf[idx:idx+BYTES_LOW], dtype=np.uint16)
    idx += BYTES_LOW

    tl = struct.unpack("<I", buf[idx:idx+BYTES_TL])[0]
    # idx += BYTES_TL  # not used further

    # — grab the averaged thermistor count from the last 2 bytes —
    avg_ct = struct.unpack('<H', buf[-BYTES_AG:])[0]

    # build time axes
    dt_high = th / S_HIGH
    dt_low  = tl / S_LOW
    t_high  = np.arange(S_HIGH) * dt_high
    t_low   = np.arange(S_LOW)  * dt_low + t_high[-1] + dt_high

    # convert volts
    v_h = vh * ADC_SCALE
    v_l = vl * ADC_SCALE

    # temperature
    v_th = avg_ct * ADC_SCALE
    R_th = 1000 * v_th / (V_REF - v_th)
    T    = pt1000_lookup(R_th)

    # plot
    print(f"High-speed: avg {dt_high:.2f} µs/sample")
    print(f"Low-speed:  avg {dt_low:.2f} µs/sample")
    print(f"{T:.1f} °C")

    plt.figure(figsize=(10,6))
    plt.plot(t_high, v_h, label="High-speed")
    plt.plot(t_low,  v_l, label="Low-speed")
    plt.xlabel("Time (µs)")
    plt.ylabel("Voltage (V)")
    plt.title(f"Decay Curve @ {T:.1f}°C")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
