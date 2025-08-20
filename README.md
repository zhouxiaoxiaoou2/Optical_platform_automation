# Optical_platform_automation

Controlling scientific instruments (lasers, spectrometers, detectors) is often locked behind vendor-provided SDKs, typically written in C/C++ and exposed via proprietary .dll libraries.  
This makes automation difficult for researchers who prefer scripting in Python.

This project reimplements vendor SDK calls in **pure Python**, wrapping the required device APIs into clean, scriptable classes.  
It allows users to:

- Control a Stradus laser via USB HID protocol  
- Operate a Shamrock spectrometer (with CCD) via vendor DLLs  
- Automate common tasks such as turning lasers on/off, setting power, scanning wavelengths, and acquiring spectra  
- Integrate these devices into Python-based experimental workflows (e.g., automation, data collection, machine learning)  

By providing a **Python interface for laboratory hardware**, this repo lowers the barrier for reproducible research and experiment automation.  
It demonstrates not only practical knowledge of experimental physics, but also **software engineering skills**: abstraction, API design, and hardware–software integration.
