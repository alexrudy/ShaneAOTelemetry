# -*- coding: utf-8 -*-
"""
Helpers for telemetry fixers.
"""
import datetime
import os
import re
from astropy.io import fits

def update(filename, header, name):
    """Update header values."""
    with fits.open(filename, mode='update') as hdus:
        hdus[0].header.update(header)
        hdus[0].header.add_history("Fixed header values on {:%Y-%m-%d} with {:s}".format(
            datetime.date.today(), name))
    
INDEXRE = re.compile(r"Data_([\d]{4})\.fits")
def get_index(filename):
    """Get the index"""
    m = INDEXRE.search(os.path.basename(filename))
    if m:
        return int(m.group(1))
    raise ValueError("Can't determine index for filename {0}".format(filename))

