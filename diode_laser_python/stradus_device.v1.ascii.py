
# -*- coding: utf-8 -*-
"""
stradus_device.v1.ascii.py
--------------------------
ASCII-framed HID transport for Stradus laser (template).
Sends raw ASCII commands into the HID payload (padding with zeros).

Requirements:
    pip install hidapi

Usage examples:
    python stradus_device.v1.ascii.py --list
    python stradus_device.v1.ascii.py --path "<DEVICE_PATH_BYTES_REPR_OR_STRING>" on
    python stradus_device.v1.ascii.py --vid 0x0C80 --pid 0x0001 power 20
    python stradus_device.v1.ascii.py --vid 0x0C80 --pid 0x0001 status
"""

import sys
import argparse
from typing import Optional
import hid


REPORT_ID = 0x00         # Most HID devices use ReportID=0 when only one report exists
PAYLOAD_LEN = 64         # HID payload length (excluding report ID); adjust if your device differs


class StradusDeviceASCII:
    def __init__(self, path: Optional[bytes] = None, vid: Optional[int] = None, pid: Optional[int] = None, timeout_ms: int = 500):
        self._dev = hid.device()
        self._timeout = timeout_ms
        self._path = path
        self._vid = vid
        self._pid = pid

    @staticmethod
    def enumerate():
        """Yield HID device dicts (raw from hid.enumerate())."""
        for d in hid.enumerate():
            yield d

    def open(self):
        if self._path is not None:
            # path may be bytes or str
            path = self._path if isinstance(self._path, (bytes, bytearray)) else str(self._path).encode('utf-8', 'ignore')
            self._dev.open_path(path)
        elif self._vid is not None and self._pid is not None:
            self._dev.open(self._vid, self._pid)
        else:
            raise ValueError("Provide device path OR vid+pid.")
        self._dev.set_nonblocking(True)

    def close(self):
        try:
            self._dev.close()
        except Exception:
            pass

    def _write_ascii(self, ascii_cmd: str):
        """Send an ASCII command framed as: [ReportID][ASCII][0x00 padding]."""
        payload = ascii_cmd.encode('ascii', 'ignore')
        if len(payload) > PAYLOAD_LEN:
            raise ValueError(f"Command too long for payload ({len(payload)} > {PAYLOAD_LEN}).")
        report = bytes([REPORT_ID]) + payload.ljust(PAYLOAD_LEN, b'\x00')
        n = self._dev.write(report)
        if n <= 0:
            raise IOError("HID write failed")

    def _read_ascii(self) -> str:
        """Read one HID report and decode as ASCII (strip zeros/CR/LF)."""
        data = self._dev.read(PAYLOAD_LEN + 1, timeout_ms=self._timeout)
        if not data:
            return ""
        payload = bytes([b for b in data[1:] if b != 0])
        try:
            return payload.decode('ascii', 'ignore').strip('\r\n\0')
        except Exception:
            # Return hex if ASCII decode fails
            return payload.hex()

    # ---- High-level laser API (adjust commands to your model) ---- #
    def laser_on(self):
        self._write_ascii("LON\r")
        return self._read_ascii()

    def laser_off(self):
        self._write_ascii("LOFF\r")
        return self._read_ascii()

    def set_power(self, mw: float):
        self._write_ascii(f"LPOWER {mw:.3f}\r")
        return self._read_ascii()

    def status(self):
        self._write_ascii("STATUS?\r")
        return self._read_ascii()


def _print_enum():
    for d in StradusDeviceASCII.enumerate():
        vid = f"0x{d['vendor_id']:04x}"
        pid = f"0x{d['product_id']:04x}"
        print(f"{vid} {pid} {d.get('manufacturer_string')} | {d.get('product_string')}")
        print(f"PATH: {d['path']!r}")
        print("-"*60)
# Results would be like: 0x0C80 0x0001 Vortran Laser Technology| Stradus Laser
# PATH: b'\\?\hid#vid_1fc9&pid_1234#7&2af9&0&000#{4d1e5b2-f1f-11cf-8cb-00100030}'

def main(argv=None):
    argv = argv or sys.argv[1:]
    p = argparse.ArgumentParser(description="Stradus laser (ASCII HID)")
    p.add_argument("--list", action="store_true", help="List HID devices and exit")
    p.add_argument("--path", type=str, help="Windows HID device path (string or bytes-repr)")
    p.add_argument("--vid", type=lambda x: int(x, 0), help="Vendor ID (e.g., 0x0C80)")
    p.add_argument("--pid", type=lambda x: int(x, 0), help="Product ID (e.g., 0x0001)")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("on")
    sub.add_parser("off")
    pp = sub.add_parser("power"); pp.add_argument("mw", type=float)
    sub.add_parser("status")
    args = p.parse_args(argv)

    if args.list:
        _print_enum()
        return 0

    # Allow bytes-repr path like b'...'
    path = None
    if args.path:
        if args.path.startswith("b'") or args.path.startswith('b\"'):
            # Evaluate bytes literal safely
            path = eval(args.path)
        else:
            path = args.path.encode('utf-8', 'ignore')

    dev = StradusDeviceASCII(path=path, vid=args.vid, pid=args.pid)
    dev.open()
    try:
        if args.cmd == "on":
            print(dev.laser_on())
        elif args.cmd == "off":
            print(dev.laser_off())
        elif args.cmd == "power":
            print(dev.set_power(args.mw))
        elif args.cmd == "status":
            print(dev.status())
        else:
            p.print_help()
            return 1
    finally:
        dev.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
