
# -*- coding: utf-8 -*-
"""
stradus_device.v2.cmd.py
------------------------
Command/length framed HID transport for Stradus laser (template).
Frames payload as: [ReportID][CmdID][Len][Data...][(optional CRC)][padding].

Requirements:
    pip install hidapi

Usage examples:
    python stradus_device.v2.cmd.py --list
    python stradus_device.v2.cmd.py --path "<DEVICE_PATH_BYTES_REPR_OR_STRING>" on
    python stradus_device.v2.cmd.py --vid 0x0C80 --pid 0x0001 power 20
    python stradus_device.v2.cmd.py --vid 0x0C80 --pid 0x0001 status
"""

import sys
import argparse
from typing import Optional, Tuple
import hid

REPORT_ID = 0x00
PAYLOAD_LEN = 64  # excluding report id

# Request/Response command IDs (align to your device's manual)
SET_CMD_QRY           = 0xA0  # "send command/query" (example)
GET_RESPONSE_STATUS   = 0xA1  # "poll response status"
GET_RESPONSE          = 0xA2  # "read response data"
SET_RESPONSE_RECEIVED = 0xA3  # "acknowledge response received"


class StradusDeviceCMD:
    def __init__(self, path: Optional[bytes] = None, vid: Optional[int] = None, pid: Optional[int] = None, timeout_ms: int = 500):
        self._dev = hid.device()
        self._timeout = timeout_ms
        self._path = path
        self._vid = vid
        self._pid = pid

    @staticmethod
    def enumerate():
        for d in hid.enumerate():
            yield d

    def open(self):
        if self._path is not None:
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

    # --------- Framing helpers ---------
    def _frame(self, cmd: int, data: bytes, add_crc: bool = False) -> bytes:
        """Build one HID report with [RID][Cmd][Len][Data][CRC?][pad]."""
        if len(data) > (PAYLOAD_LEN - 2):  # 2 bytes used by cmd/len; CRC not considered here
            raise ValueError("Data too long for single report")
        payload = bytearray(PAYLOAD_LEN)
        payload[0] = cmd & 0xFF
        payload[1] = len(data) & 0xFF
        payload[2:2+len(data)] = data
        if add_crc:
            # Example CRC-8 placeholder (replace with the real CRC if manual requires it)
            crc = 0
            for b in data:
                crc ^= b
            payload[2+len(data)] = crc & 0xFF
        report = bytes([REPORT_ID]) + bytes(payload)
        return report

    def _write(self, report: bytes):
        n = self._dev.write(report)
        if n <= 0:
            raise IOError("HID write failed")

    def _read(self) -> bytes:
        return bytes(self._dev.read(PAYLOAD_LEN + 1, timeout_ms=self._timeout))

    # --------- Low-level request/response (single frame) ---------
    def send_request(self, cmd: int, data: bytes = b"", add_crc: bool = False):
        self._write(self._frame(cmd, data, add_crc=add_crc))

    def read_response(self) -> Tuple[int, bytes]:
        """
        Read one response frame. Returns (status_or_cmd, payload_bytes).
        Expect format: [RID][Cmd/Status][Len][Data...]
        """
        raw = self._read()
        if not raw:
            return (-1, b"")
        cmd = raw[1]
        length = raw[2] if len(raw) > 2 else 0
        payload = raw[3:3+length] if len(raw) >= 3+length else raw[3:]
        return (cmd, bytes(payload))

    # --------- High-level laser API (ASCII commands tunneled inside CMD frame) ---------
    def laser_on(self):
        self.send_request(SET_CMD_QRY, b"LON\r")
        _, payload = self.read_response()
        return self._decode_ascii(payload)

    def laser_off(self):
        self.send_request(SET_CMD_QRY, b"LOFF\r")
        _, payload = self.read_response()
        return self._decode_ascii(payload)

    def set_power(self, mw: float):
        self.send_request(SET_CMD_QRY, f"LPOWER {mw:.3f}\r".encode("ascii"))
        _, payload = self.read_response()
        return self._decode_ascii(payload)

    def status(self):
        self.send_request(SET_CMD_QRY, b"STATUS?\r")
        _, payload = self.read_response()
        return self._decode_ascii(payload)

    @staticmethod
    def _decode_ascii(b: bytes) -> str:
        try:
            return b.decode('ascii', 'ignore').strip('\r\n\0')
        except Exception:
            return b.hex()


def _print_enum():
    for d in StradusDeviceCMD.enumerate():
        vid = f"0x{d['vendor_id']:04x}"
        pid = f"0x{d['product_id']:04x}"
        print(f"{vid} {pid} {d.get('manufacturer_string')} | {d.get('product_string')}")
        print(f"PATH: {d['path']!r}")
        print("-"*60)


def main(argv=None):
    argv = argv or sys.argv[1:]
    p = argparse.ArgumentParser(description="Stradus laser (CMD HID)")
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

    path = None
    if args.path:
        if args.path.startswith("b'") or args.path.startswith('b\"'):
            path = eval(args.path)
        else:
            path = args.path.encode('utf-8', 'ignore')

    dev = StradusDeviceCMD(path=path, vid=args.vid, pid=args.pid)
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
