#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os, datetime, re
from telemetry.fixer import get_index, update
from astropy.utils.console import ProgressBar

DEFAULT_MATRIX = "controlMatrix_16x.fits"
BOOSTED_MATRIX = "controlMatrix_16x.incgain.RUDY.fits"

CM_RANGES = [
    (0, 39, BOOSTED_MATRIX),
]

def find_cm(index):
    """Find the CM, the dumb way."""
    for start, stop, name in CM_RANGES:
        if start <= index <= stop:
            return name
    else:
        raise ValueError("Couldn't figure out index {0}.".format(index))
        

def main():
    """Show all the datasets."""
    root = "/Volumes/LaCie/Telemetry2"
    path = "ShaneAO/2016-03-16/"
    script = os.path.basename(__file__)
    search = glob.glob(os.path.join(root, path, "raw", "*.fits"))
    for filename in ProgressBar(search):
        index = get_index(filename)
        control_matrix = find_cm(index)
        update(filename, {"CONTROLM":control_matrix}, script)

if __name__ == '__main__':
    main()