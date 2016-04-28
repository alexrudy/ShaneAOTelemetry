#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os, datetime
from telemetry.fixer import get_index, update
from astropy.utils.console import ProgressBar


DEFAULT_MATRIX = "controlMatrix_16x.fits"
DEFAULT_REFCENTS = "refcents_16x.fits"
CM_RANGES = [
    (0, 55, (DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    (56, 105, (DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    (106, 155, ("controlMatrix_16x.incgain.250Hz.fits", DEFAULT_REFCENTS)),
    (156, 203, ("controlMatrix_16x.incgain.1000Hz.fits", DEFAULT_REFCENTS)),
    (204, 253, (DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    (254, 303, (DEFAULT_MATRIX, "refcents_16x.1000Hz.fits")),
    (304, 353, ("controlMatrix_16x.incgain.250Hz.fits", DEFAULT_REFCENTS)),
    (354, 403, ("controlMatrix_16x.incgain.250Hz.fits", "refcents_16x.1000Hz.fits")),
    (404, 453, ("controlMatrix_16x.incgain.1000Hz.fits", "refcents_16x.1000Hz.fits")),
    (454, 503, (DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    (504, 553, (DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    (554, 603, (DEFAULT_MATRIX, "refcents_16x.1000Hz.fits")),
    (604, 653, ("controlMatrix_16x.incgain.250Hz.fits", DEFAULT_REFCENTS)),
    (654, 753, ("controlMatrix_16x.incgain.250Hz.fits", "refcents_16x.1000Hz.fits")),
    (754, 803, ("controlMatrix_16x.incgain.250Hz.fits", DEFAULT_REFCENTS)),
    (804, 1023,(DEFAULT_MATRIX, DEFAULT_REFCENTS)),
    
]

def find_cm(index):
    """Find the CM, the dumb way."""
    for start, stop, name in CM_RANGES:
        if start <= index <= stop:
            return name
    else:
        raise ValueError("Couldn't figure out index {0}".format(index))

def main():
    """Show all the datasets."""
    root = "/Volumes/LaCie/Telemetry2"
    path = "ShaneAO/2016-04-18/"
    script = os.path.basename(__file__)
    search = glob.glob(os.path.join(root, path, "raw", "*.fits"))
    for filename in ProgressBar(search):
        index = get_index(filename)
        parameters = dict(zip(["CONTROLM", "REFCENT_"], find_cm(index)))
        update(filename, parameters, script)

if __name__ == '__main__':
    main()
