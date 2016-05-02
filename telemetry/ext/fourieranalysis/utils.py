# -*- coding: utf-8 -*-
import numpy as np
import astropy.units as u

def frequencies(length, rate):
    """Make a frequency array."""
    length = int(length)
    rate = u.Quantity(rate, u.Hz)
    return (np.mgrid[-length//2:length//2].astype(np.float) / length) * rate
