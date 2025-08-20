# Spectroscopy Control (Python)

This project provides a **Python wrapper** around the Andor **Shamrock spectrometer** DLL (`ShamrockCIF.dll`) using `ctypes`.  
It allows you to **initialize the device, query hardware info, set/get grating and wavelength, read calibration data, acquire spectra** (if supported by the DLL), and **save/plot results**.

---

## Requirements
- Windows (32/64-bit, must match your DLL + Python)
- `ShamrockCIF.dll` (from vendor SDK)  
  Place it in the same directory as `spectroscopy.py` or add it to your system `PATH`.
- Python ≥ 3.8
- Python packages:
```bash
  pip install numpy matplotlib
```

## Usage
- Check device info
```Python spectroscopy.py info```
Example output:
Devices: 1
Serial: SR1245

- Query wavelength range & pixel count
```python spectroscopy.py limits```
```python spectroscopy.py pixels```

- Calibration (first 10 points)
```python spectroscopy.py calib```

- Control grating / wavelength

     ```python spectroscopy.py grating 1          # set grating index to 1```

    ```python spectroscopy.py get-grating        # read current grating```

    ```python spectroscopy.py wavelength 532     # set central wavelength to 532 nm```

    ```python spectroscopy.py get-wavelength     # query central wavelength```

- Acquire spectrum

   ```python spectroscopy.py acquire --outfile spectrum.csv ```

- Options:

    `--start / --end` → limit wavelength range (nm)

    `--points` → resample to fixed number of points (e.g. 1024)

    `--outfile` → output CSV filename (default: `spectrum.csv`)

    Note: Some DLL versions do not export ShamrockAcquire.
    In that case, this command will raise NotImplementedError.
    This is expected: Shamrock controls the optics, while the detector SDK handles intensity acquisition.

- Plot saved spectrum

   ```python spectroscopy.py plot spectrum.csv```

- Example workflow

   ```spectroscopy.py info  # check device```

   ```python spectroscopy.py wavelength 600  # set central wavelength```

   ```python spectroscopy.py acquire --start 400 --end 700 --points 1024 --outfile test.csv # acquire between 400–700 nm, resample to 1024 points```

   ```python spectroscopy.py plot test.csv # plot result```

