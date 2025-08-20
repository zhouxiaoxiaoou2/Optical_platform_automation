# spectroscopy.py
# Python wrapper for Andor Shamrock spectrometer via ShamrockCIF.dll
# Function：Initialization/Closing, Device Enumeration, Serial Number, Grating Settings/Queries, Central Wavelength Settings/Queries,
#      Pixel Count, Wavelength Calibration, Acquisition (if provided by DLL), Save CSV, Plotting

import os
import sys
import argparse
import ctypes
from ctypes import byref, c_int, c_double, c_char_p, create_string_buffer

# Optional dependencies: used for acquire/plot
try:
    import numpy as np
except Exception:
    np = None

# ---------- DLL 加载 ----------
DLL_NAME = "ShamrockCIF.dll"

def _load_dll():
    # first try to load from the script directory
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(here, DLL_NAME)
    if os.path.exists(candidate):
        return ctypes.WinDLL(candidate)
    return ctypes.WinDLL(DLL_NAME)

try:
    sh = _load_dll()
except Exception as e:
    raise RuntimeError(f"Unable to load {DLL_NAME}, please place the DLL in the same directory as the script or add it to the system PATH. Original error: {e}")

# Common success return code (Andor/Shamrock typically uses 20202 to indicate success)
SHAMROCK_SUCCESS = 20202

# ---------- Declare API prototypes (based on common SDK signatures and VB Declare) ----------
# Initialization/Closing
sh.ShamrockInitialize.argtypes = [c_char_p]
sh.ShamrockInitialize.restype  = c_int
sh.ShamrockClose.argtypes      = []
sh.ShamrockClose.restype       = c_int

# Device enumeration, serial number, error description
sh.ShamrockGetNumberDevices.argtypes = [ctypes.POINTER(c_int)]
sh.ShamrockGetNumberDevices.restype  = c_int
sh.ShamrockGetSerialNumber.argtypes  = [c_int, ctypes.c_char_p]
sh.ShamrockGetSerialNumber.restype   = c_int
sh.ShamrockGetFunctionReturnDescription.argtypes = [c_int, ctypes.c_char_p, c_int]
sh.ShamrockGetFunctionReturnDescription.restype  = c_int

# Grating, central wavelength
sh.ShamrockSetGrating.argtypes = [c_int, c_int]
sh.ShamrockSetGrating.restype  = c_int
sh.ShamrockGetGrating.argtypes = [c_int, ctypes.POINTER(c_int)]
sh.ShamrockGetGrating.restype  = c_int
sh.ShamrockSetWavelength.argtypes = [c_int, c_double]
sh.ShamrockSetWavelength.restype  = c_int
sh.ShamrockGetWavelength.argtypes = [c_int, ctypes.POINTER(c_double)]
sh.ShamrockGetWavelength.restype  = c_int

# Pixel count, calibration, wavelength limits
sh.ShamrockGetNumberPixels.argtypes = [c_int, ctypes.POINTER(c_int)]
sh.ShamrockGetNumberPixels.restype  = c_int
sh.ShamrockGetCalibration.argtypes  = [c_int, ctypes.POINTER(c_double), c_int]
sh.ShamrockGetCalibration.restype   = c_int
sh.ShamrockGetWavelengthLimits.argtypes = [c_int, ctypes.POINTER(c_double), ctypes.POINTER(c_double)]
sh.ShamrockGetWavelengthLimits.restype  = c_int

# Acquisition (if not all DLL versions export)
_has_acquire = hasattr(sh, "ShamrockAcquire")
if _has_acquire:
    sh.ShamrockAcquire.argtypes = [c_int, ctypes.POINTER(c_double), c_int]
    sh.ShamrockAcquire.restype  = c_int

# ---------- mistake check ----------
def _errcheck(ret: int, funcname: str):
    if ret == SHAMROCK_SUCCESS:
        return
    # take error description
    try:
        buf = create_string_buffer(256)
        sh.ShamrockGetFunctionReturnDescription(ret, buf, 256)
        desc = buf.value.decode(errors="ignore")
    except Exception:
        desc = ""
    raise RuntimeError(f"{funcname} failed (code={ret}) {desc}")

# ---------- top package----------
class ShamrockSpectrometer:
    def __init__(self, device: int = 0):
        self.dev = device
        _errcheck(sh.ShamrockInitialize(b""), "ShamrockInitialize")

    def close(self):
        _errcheck(sh.ShamrockClose(), "ShamrockClose")

    # Device information
    def get_num_devices(self) -> int:
        n = c_int()
        _errcheck(sh.ShamrockGetNumberDevices(byref(n)), "ShamrockGetNumberDevices")
        return n.value

    def get_serial(self, device: int = None) -> str:
        dev = self.dev if device is None else device
        buf = create_string_buffer(64)
        _errcheck(sh.ShamrockGetSerialNumber(dev, buf), "ShamrockGetSerialNumber")
        return buf.value.decode(errors="ignore").strip()

    # Grating, central wavelength
    def set_grating(self, grating: int):
        _errcheck(sh.ShamrockSetGrating(self.dev, grating), "ShamrockSetGrating")

    def get_grating(self) -> int:
        g = c_int()
        _errcheck(sh.ShamrockGetGrating(self.dev, byref(g)), "ShamrockGetGrating")
        return g.value

    def set_wavelength(self, nm: float):
        _errcheck(sh.ShamrockSetWavelength(self.dev, c_double(nm)), "ShamrockSetWavelength")

    def get_wavelength(self) -> float:
        x = c_double()
        _errcheck(sh.ShamrockGetWavelength(self.dev, byref(x)), "ShamrockGetWavelength")
        return x.value

    # Pixel count, calibration, wavelength limits
    def get_pixel_count(self) -> int:
        n = c_int()
        _errcheck(sh.ShamrockGetNumberPixels(self.dev, byref(n)), "ShamrockGetNumberPixels")
        return n.value

    def get_wavelength_limits(self):
        lo = c_double(); hi = c_double()
        _errcheck(sh.ShamrockGetWavelengthLimits(self.dev, byref(lo), byref(hi)), "ShamrockGetWavelengthLimits")
        return lo.value, hi.value

    def get_calibration(self):
        npx = self.get_pixel_count()
        arr = (c_double * npx)()
        _errcheck(sh.ShamrockGetCalibration(self.dev, arr, npx), "ShamrockGetCalibration")
        return [arr[i] for i in range(npx)]

    # Acquisition (if not all DLL versions export)
    def acquire(self):
        if not _has_acquire:
            raise NotImplementedError(
                "This DLL version does not export ShamrockAcquire; please use the Andor camera SDK (ATMCD) for intensity acquisition,"
                "Shamrock is responsible for optics/calibration."
            )
        npx = self.get_pixel_count()
        buf = (c_double * npx)()
        _errcheck(sh.ShamrockAcquire(self.dev, buf, npx), "ShamrockAcquire")
        return [buf[i] for i in range(npx)]

# ---------- CLI ----------
def _cli(argv=None):
    argv = argv or sys.argv[1:]
    ap = argparse.ArgumentParser(description="Shamrock Spectrometer (Python ctypes)")
    ap.add_argument("--device", type=int, default=0, help="device index, default=0")

    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("init", help="initialize and keep session for chained ops")
    sub.add_parser("info", help="list num devices and serial of current device")
    sub.add_parser("limits", help="print wavelength limits (nm)")
    sub.add_parser("pixels", help="print number of CCD pixels")
    sub.add_parser("calib", help="print first 10 wavelength calibration points")
    sub.add_parser("get-grating", help="query current grating index")
    sub.add_parser("get-wavelength", help="query current central wavelength (nm)")

    pg = sub.add_parser("grating", help="set grating index")
    pg.add_argument("g", type=int)

    pw = sub.add_parser("wavelength", help="set central wavelength (nm)")
    pw.add_argument("nm", type=float)

    pacq = sub.add_parser("acquire", help="acquire spectrum (if DLL provides)")
    pacq.add_argument("--start", type=float, default=None, help="optional lower wavelength bound (nm) for saving")
    pacq.add_argument("--end",   type=float, default=None, help="optional upper wavelength bound (nm) for saving")
    pacq.add_argument("--points", type=int,  default=None, help="optional number of points to resample when saving")
    pacq.add_argument("--outfile", type=str, default="spectrum.csv", help="CSV output path (default: spectrum.csv)")

    pplot = sub.add_parser("plot", help="plot a saved CSV")
    pplot.add_argument("csv", type=str, help="CSV path produced by 'acquire'")

    args = ap.parse_args(argv)

    # Only plot does not require DLL connection
    if args.cmd == "plot":
        if np is None:
            print("Requires numpy and matplotlib for plotting: pip install numpy matplotlib")
            return 1
        import matplotlib.pyplot as plt
        import csv

        wl = []; inten = []
        with open(args.csv, "r", newline="") as f:
            r = csv.reader(f)
            header = next(r, None)  # skip header
            for row in r:
                try:
                    wl.append(float(row[0])); inten.append(float(row[1]))
                except Exception:
                    continue
        plt.figure()
        plt.plot(wl, inten)
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Intensity (a.u.)")
        plt.title(os.path.basename(args.csv))
        plt.tight_layout()
        plt.show()
        return 0

    # Other commands require device connection
    sp = ShamrockSpectrometer(device=args.device)
    try:
        if args.cmd == "init":
            print("Initialized.")
        elif args.cmd == "info":
            n = sp.get_num_devices()
            print("Devices:", n)
            try:
                print("Serial :", sp.get_serial())
            except Exception as e:
                print("Serial : <unavailable>", e)
        elif args.cmd == "limits":
            lo, hi = sp.get_wavelength_limits()
            print(f"Wavelength limits: {lo:.2f} .. {hi:.2f} nm")
        elif args.cmd == "pixels":
            print("Pixels =", sp.get_pixel_count())
        elif args.cmd == "calib":
            calib = sp.get_calibration()
            print("First 10 wavelength calib:", [round(x, 3) for x in calib[:10]], " ...")
        elif args.cmd == "get-grating":
            print("Grating =", sp.get_grating())
        elif args.cmd == "get-wavelength":
            print(f"Wavelength = {sp.get_wavelength():.3f} nm")
        elif args.cmd == "grating":
            sp.set_grating(args.g)
            print("Grating set to", args.g)
        elif args.cmd == "wavelength":
            sp.set_wavelength(args.nm)
            print(f"Wavelength set to {args.nm:.3f} nm")
        elif args.cmd == "acquire":
            if np is None:
                print("Requires numpy for saving CSV: pip install numpy")
                return 1
            # Acquire intensity (if not all DLL versions export)
            intens = sp.acquire()
            wl = sp.get_calibration()
            if len(wl) != len(intens):
                # In rare cases, calibration and intensity lengths may differ, so we trim
                n = min(len(wl), len(intens))
                wl = wl[:n]; intens = intens[:n]

            # Optional wavelength filtering
            if args.start is not None or args.end is not None:
                lo = args.start if args.start is not None else -float("inf")
                hi = args.end   if args.end   is not None else  float("inf")
                mask = [(lo <= w <= hi) for w in wl]
                wl   = [w for w, m in zip(wl, mask) if m]
                intens = [y for y, m in zip(intens, mask) if m]

            # Optional resampling
            if args.points and len(wl) > 1:
                # Simple linear resampling to uniform grid
                import numpy as _np
                wmin, wmax = wl[0], wl[-1]
                if wmin > wmax:
                    wmin, wmax = wmax, wmin
                    wl = wl[::-1]; intens = intens[::-1]
                new_w = _np.linspace(wmin, wmax, args.points)
                new_i = _np.interp(new_w, _np.array(wl), _np.array(intens))
                wl, intens = new_w.tolist(), new_i.tolist()

            # Save CSV
            import csv
            with open(args.outfile, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Wavelength(nm)", "Intensity"])
                for x, y in zip(wl, intens):
                    w.writerow([x, y])
            print("Saved CSV ->", args.outfile)
        else:
            ap.print_help()
            return 1
    finally:
        sp.close()

    return 0

if __name__ == "__main__":
    raise SystemExit(_cli())
