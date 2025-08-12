import zipfile
import struct
import numpy as np

# ====== CONFIG ======
ZIP_PATH = r"C:\Users\klipk\Downloads\EmptyCellAugust.zip"  # <-- change me
R_DISCHARGE_OHM = 1_000_000  # your series resistor = 1 MΩ

# ADC / framing (must match Teensy sketch)
V_REF = 3.3
ADC_MAX_10 = 1023.0   # 10-bit
ADC_MAX_12 = 4095.0   # 12-bit

S_HIGH  = 50
S_LOW   = 16000

BYTES_H   = S_HIGH * 2          # uint16_t * S_HIGH
BYTES_TH  = 4                   # unsigned long (t_high, µs)
BYTES_L   = S_LOW * 2           # uint16_t * S_LOW
BYTES_TL1 = 4                   # unsigned long (totalLow1, µs)
BYTES_TL2 = 4                   # unsigned long (totalLow, µs)
BYTES_AG  = 4                   # float (avgTherm ADC counts)
TOTAL     = BYTES_H + BYTES_TH + BYTES_L + BYTES_TL1 + BYTES_TL2 + BYTES_AG

# Simple PT1000 lookup via linear interpolation (same table you used)
def pt1000_lookup(R):
    T_ref = np.array([-79, -70, -60, -50, -40, -30, -20, -10, 0, 10, 20, 30], dtype=float)
    R_ref = np.array([687.30, 723.30, 763.30, 803.10, 842.70, 882.20, 921.60, 960.90,
                      1000.00, 1039.00, 1077.90, 1116.70], dtype=float)
    return float(np.interp(R, R_ref, T_ref))

def parse_one_blob(raw):
    """Parse one binary record -> (t_all_us, v_all_V, temp_C)"""
    if len(raw) != TOTAL:
        raise ValueError(f"Bad blob size {len(raw)} (expected {TOTAL})")

    idx = 0
    vh = np.frombuffer(raw[idx:idx+BYTES_H], dtype=np.uint16); idx += BYTES_H
    t_high = struct.unpack('<I', raw[idx:idx+BYTES_TH])[0]; idx += BYTES_TH
    vl = np.frombuffer(raw[idx:idx+BYTES_L], dtype=np.uint16); idx += BYTES_L
    totalLow1 = struct.unpack('<I', raw[idx:idx+BYTES_TL1])[0]; idx += BYTES_TL1
    totalLow  = struct.unpack('<I', raw[idx:idx+BYTES_TL2])[0]; idx += BYTES_TL2
    avg_ct    = struct.unpack('<f', raw[idx:idx+BYTES_AG])[0];  idx += BYTES_AG

    # Time axes (µs)
    dt_high = t_high / float(S_HIGH)
    dt_low1 = totalLow1 / 1200.0
    rem = S_LOW - 1200
    dt_low2 = (totalLow - totalLow1) / float(rem) if rem > 0 else 0.0

    th_ax   = np.arange(S_HIGH, dtype=float) * dt_high
    tl_ax1  = (th_ax[-1] + dt_high) + np.arange(1200, dtype=float) * dt_low1
    tl_ax2  = (tl_ax1[-1] + dt_low1) + np.arange(rem, dtype=float) * dt_low2
    t_all   = np.concatenate([th_ax, tl_ax1, tl_ax2])  # µs

    # Voltages
    v_high = vh * (V_REF / ADC_MAX_10)
    v_low1 = vl[:1200] * (V_REF / ADC_MAX_12)
    v_low2 = vl[1200:] * (V_REF / ADC_MAX_12)
    v_all  = np.concatenate([v_high, v_low1, v_low2])

    # Temperature from thermistor ADC (avg_ct is 10-bit counts on ADC1)
    v_th = (avg_ct / ADC_MAX_10) * V_REF
    R_REF = 1000.0  # Ω divider reference
    if V_REF - v_th <= 0:
        temp_C = float('nan')
    else:
        R_th = R_REF * v_th / (V_REF - v_th)
        temp_C = pt1000_lookup(R_th)

    return t_all, v_all, temp_C

def estimate_capacitance_pf(t_us, v, R_ohm):
    """Fit ln(v/v0) vs t to get tau, then C = tau/R. Returns pF."""
    # Basic guards
    if len(v) < 10 or v[0] <= 0:
        return np.nan
    v0 = v[0]

    # Use the falling region where 5%..100% of v0 (avoid tiny tail)
    mask = (v > 0.05 * v0) & (v < v0) & np.isfinite(v)
    if mask.sum() < 5:
        return np.nan

    t = (t_us * 1e-6).astype(float)  # seconds
    ln_ratio = np.log(v[mask] / v0)
    # Robust-ish linear fit
    slope, intercept = np.polyfit(t[mask], ln_ratio, 1)
    if slope >= 0:
        return np.nan  # not a decay
    tau_s = -1.0 / slope
    C_F = tau_s / float(R_ohm)
    return C_F * 1e12  # pF

cap_list = []
temp_list = []
names_ok = []
names_bad = []

with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
    members = [m for m in zf.infolist() if not m.is_dir()]
    # Try to be permissive: accept anything that matches size TOTAL
    for m in members:
        try:
            with zf.open(m, 'r') as fh:
                raw = fh.read()
            if len(raw) != TOTAL:
                names_bad.append((m.filename, len(raw)))
                continue

            t_us, v_V, temp_C = parse_one_blob(raw)
            c_pf = estimate_capacitance_pf(t_us, v_V, R_DISCHARGE_OHM)

            if np.isfinite(c_pf):
                cap_list.append(c_pf)
                temp_list.append(temp_C)
                names_ok.append(m.filename)
            else:
                names_bad.append((m.filename, "fit_failed"))

        except Exception as e:
            names_bad.append((m.filename, f"error: {e}"))

# ---- Report ----
if len(cap_list) == 0:
    print("No valid records found.")
else:
    caps = np.array(cap_list, dtype=float)
    temps = np.array(temp_list, dtype=float)

    print(f"Processed files (ok/total): {len(caps)}/{len(cap_list)+len(names_bad)}")
    print(f"Average capacitance: {np.nanmean(caps):.2f} pF")
    print(f"Std dev: {np.nanstd(caps):.2f} pF")
    print(f"Min / Max: {np.nanmin(caps):.2f} / {np.nanmax(caps):.2f} pF")

    if np.isfinite(temps).any():
        print(f"Average temperature: {np.nanmean(temps):.2f} °C")

    # Uncomment to see which files were included
    # for n in names_ok: print("OK  ", n)

    if names_bad:
        print("\nSkipped/failed files:")
        for n, why in names_bad[:10]:
            print(" -", n, why)
        if len(names_bad) > 10:
            print(f" ... and {len(names_bad)-10} more")
