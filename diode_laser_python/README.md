# Stradus Laser Python Driver

This repository provides **two Python drivers** for controlling a Stradus laser via USB HID.  
Depending on your hardware, you can use either the **ASCII protocol** (simple text commands) or the **CMD protocol** (binary framed commands).

- `stradus_device.v1.ascii.py` → ASCII protocol (sends commands like `LON\r`)  
- `stradus_device.v2.cmd.py` → Binary CMD protocol (wraps commands with headers and length)  

This is a personal learning + utility project, not the official driver.

Both provide the same high-level functions:  

- `open(path or vid/pid)` / `close()`  
- `laser_on()` / `laser_off()`  
- `set_power(mW)`  
- `status()`  

---

## Installation

You need Python 3.8+ and the `hidapi` wrapper:
`pip install hid`

On Linux/macOS you may also need to install libhidapi from your package manager.

## Usage
### ASCII Driver(v1)
- list HID devices:
```python stradus_device.v1.ascii.py --list```
- Connect by device path:
```python stradus_device.v1.ascii.py --path "b'\\?\hid#vid_0c80&pid_0001#7&12345...'" status```
- Connect by VID/PID:
```python stradus_device.v1.ascii.py --vid 0x0C80 --pid 0x0001 on```
- Set power (example: 5 mW):
```python stradus_device.v1.ascii.py --vid 0x0C80 --pid 0x0001 power 5.0```

### CMD Driver(v2)
- list HID devices:
```python stradus_device.v2.cmd.py --list```
- Turn on and off:
```python stradus_device.v2.cmd.py --vid 0x0C80 --pid 0x0001 on```
```python stradus_device.v2.cmd.py --vid 0x0C80 --pid 0x0001 off```
- Set power (example: 10 mW):
```python stradus_device.v2.cmd.py --vid 0x0C80 --pid 0x0001 power 10.0```


## Notes
Use --list to enumerate all HID devices. Copy the path or note down the vid/pid.

ASCII version sends human-readable commands like LON\r.

CMD version uses binary framing with cmd, length, and payload.

Both scripts internally use hid.device().write() and read() for communication.

## Why HID and not Serial?

The Stradus laser hardware in this driver communicates over USB HID (mcHID.dll on Windows).
If your hardware is serial-based instead, replace the HID code with pyserial.
