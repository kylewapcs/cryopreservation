# Optimized T-Discharge System

This folder contains the complete system for measuring dielectric decay curves using a Teensy microcontroller with optimized timing and temperature control.

## Overview

The system measures the discharge of a capacitor through a high-resistance load while simultaneously monitoring temperature. It uses a dual-speed sampling approach: high-speed sampling for the initial rapid decay, followed by low-speed sampling for the slower decay phase.

## Files Description

### Core Arduino Code

- **`optimized_tdischarge.txt`** - Arduino code to upload to Teensy microcontroller
  - Implements dual-speed sampling (high-speed + low-speed phases)
  - Measures thermistor temperature with averaging
  - Sends binary data packet via serial communication
  - **Usage**: Copy and paste this code into Arduino IDE and upload to Teensy

### Data Collection Scripts

#### `automated_loop1.py` - Main Data Collection Script

- **Purpose**: Automated data collection with live plotting and averaging
- **Features**:
  - Continuous data collection from Teensy
  - Real-time plotting of dielectric decay curves
  - Automatic averaging of multiple runs (default: 10 runs)
  - Live temperature monitoring
  - Automatic file saving with sequential naming
  - Log-log scale plotting for better visualization
- **Usage**: Run this script to start continuous data collection
- **Output**: Saves binary files to `C:\Users\klipk\Downloads\test6_logs\`

#### `plot_estimate_temp.py` - Single Measurement Script

- **Purpose**: Single-shot measurement with temperature estimation and capacitance calculation
- **Features**:
  - Single data acquisition from Teensy
  - Temperature calculation from PT1000 thermistor
  - Capacitance estimation from RC decay fitting
  - Detailed timing analysis (high-speed vs low-speed phases)
  - Normalized voltage plotting
- **Usage**: Run for single measurements with detailed analysis

#### `plot_savecbin.py` - Legacy Data Collection Script

- **Purpose**: Alternative data collection script with different timing approach
- **Features**:
  - Single measurement with file saving
  - Different voltage normalization approach
  - Temperature monitoring
  - Linear time scale plotting
- **Usage**: Alternative to `automated_loop1.py` for different analysis approaches

### Data Analysis Scripts

#### `binaryanalysis_savejpeg.py` - Binary File Analysis

- **Purpose**: Analyze saved binary files and generate plots
- **Features**:
  - Reads binary files saved by collection scripts
  - Reconstructs time and voltage data
  - Calculates temperature and capacitance
  - Generates publication-ready plots
  - Log-log scale visualization
- **Usage**: Point to a specific binary file and run for analysis
- **Configuration**: Edit `FILE_PATH` to point to your binary file

#### `july_29.ipynb` - Jupyter Notebook Analysis

- **Purpose**: Interactive analysis and experimentation
- **Features**:
  - Interactive data analysis
  - Real-time data collection
  - Custom plotting and analysis
  - Experimental parameter testing
- **Usage**: Open in Jupyter Notebook for interactive analysis

## Data Binning and Analysis

**`merge_kyle_data_and_save.ipynb`** (in parent directory) - Data Binning Script

- **Purpose**: Processes multiple binary files and bins data by temperature
- **Features**:
  - Loads multiple binary files from ZIP archives
  - Bins data by temperature (5°C intervals)
  - Averages data within temperature bins
  - Exports processed data for further analysis
- **Usage**: Point to ZIP file containing multiple binary files and run

## System Configuration

### Hardware Setup

- **Teensy Microcontroller**: Handles data acquisition
- **Charge Pin**: Pin 13 for capacitor charging
- **Voltage Pin**: A1 (ADC0) for voltage measurement
- **Thermistor Pin**: A8 (ADC1) for temperature measurement
- **Serial Communication**: 115200 baud rate

### Key Parameters

- **S_HIGH**: 50 samples (high-speed phase)
- **S_LOW**: 16000 samples (low-speed phase)
- **T_SAMPLES**: 500 thermistor readings for averaging
- **V_REF**: 3.3V reference voltage
- **R_REF**: 1000Ω reference resistance

### Data Packet Structure

Each binary packet contains:

1. High-speed voltage data (S_HIGH × uint16)
2. High-speed timing (uint32)
3. Low-speed voltage data (S_LOW × uint16)
4. Low-speed timing phase 1 (uint32)
5. Low-speed timing phase 2 (uint32)
6. Average thermistor reading (float32)

## Usage Workflow

1. **Setup**: Upload `optimized_tdischarge.txt` to Teensy
2. **Data Collection**: Run `automated_loop1.py` for continuous collection
3. **Analysis**: Use `binaryanalysis_savejpeg.py` for individual file analysis
4. **Bulk Processing**: Use `merge_kyle_data_and_save.ipynb` for temperature-binned analysis

## Temperature Calculation

The system uses a PT1000 thermistor with lookup table interpolation:

- Temperature range: -79°C to +30°C
- Resistance range: 687.30Ω to 1116.70Ω
- Linear interpolation between reference points

## Capacitance Estimation

Capacitance is calculated from RC decay fitting:

- Fits exponential decay to voltage vs time data
- Uses time constant (τ = RC) to calculate capacitance
- Results in picoFarad (pF) units

## File Naming Convention

- Binary files: `teensy_raw_N.bin` (where N is sequential number)
- Timestamped files: `teensy_raw_YYYYMMDD_HHMMSS.bin`
- ZIP archives: Contain multiple binary files for bulk processing

## Dependencies

- Python packages: `numpy`, `matplotlib`, `serial`, `struct`, `time`, `os`
- Arduino libraries: `ADC.h`
- Jupyter Notebook for interactive analysis

## Notes

- All scripts assume COM9 for serial communication (edit PORT variable as needed)
- Binary files are saved to specific directories (edit RAW_DIR as needed)
- Temperature calculations assume PT1000 thermistor characteristics
- Voltage measurements use 10-bit ADC for high-speed, 12-bit for low-speed
