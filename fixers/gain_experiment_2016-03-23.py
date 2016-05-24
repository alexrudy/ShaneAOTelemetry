#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os, datetime, re
from telemetry.fixer import get_index, update
from astropy.utils.console import ProgressBar

DEFAULT_MATRIX = "controlMatrix_16x.fits"
BOOSTED_MATRIX = "controlMatrix_16x.incgain.250Hz.fits"

CM_RANGES = [
    (0, 22, DEFAULT_MATRIX),
    (23, 42, BOOSTED_MATRIX),
    (43, 62, DEFAULT_MATRIX),
    (63, 82, BOOSTED_MATRIX),
    (83, 102, DEFAULT_MATRIX),
    (103,122, BOOSTED_MATRIX),
    (123,142, DEFAULT_MATRIX),
    (143,162, BOOSTED_MATRIX),
    (163,182, DEFAULT_MATRIX),
    (183,195, BOOSTED_MATRIX),
    (196,215, DEFAULT_MATRIX),
    (216,235, BOOSTED_MATRIX),
    (236,255, DEFAULT_MATRIX),
    (256,275, BOOSTED_MATRIX),
    (276,295, DEFAULT_MATRIX),
    (296,315, BOOSTED_MATRIX),
    (316,335, DEFAULT_MATRIX),
    (336,355, BOOSTED_MATRIX),
    (356,375, DEFAULT_MATRIX),
    (376,395, BOOSTED_MATRIX),
    (396,425, DEFAULT_MATRIX),
    (426,445, BOOSTED_MATRIX)
]

index = max(items[1] for items in CM_RANGES) + 1
for start, stop, cm in CM_RANGES:
    if stop == index - 1:
        last = cm
        nex = BOOSTED_MATRIX if last == DEFAULT_MATRIX else DEFAULT_MATRIX
        break

while index <= 556:
    CM_RANGES.append((index, index+19, nex))
    nex, last = last, nex
    index += 20

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
    path = "ShaneAO/2016-03-23/"
    script = os.path.basename(__file__)
    search = glob.glob(os.path.join(root, path, "raw", "*.fits"))
    for filename in ProgressBar(search):
        index = get_index(filename)
        control_matrix = find_cm(index)
        update(filename, {"CONTROLM":control_matrix}, script)

if __name__ == '__main__':
    main()