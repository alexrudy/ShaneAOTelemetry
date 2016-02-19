# -*- coding: utf-8 -*-
"""View tools for periodograms"""

import astropy.units as u
import numpy as np

from ..models.periodogram import frequencies

def show_periodogram(ax, periodogram, rate=1.0, **kwargs):
    """Show a periodogram on an axis."""
    rate = u.Quantity(rate, u.Hz)
    kwargs.setdefault('alpha', 0.1)
    kwargs.setdefault('color', 'b')
    length = periodogram.shape[0]
    lines = ax.plot(frequencies(length, rate).value, periodogram, **kwargs)
    ax.set_xlabel("Frequency ({})".format(rate.unit))
    ax.set_yscale("log")
    return lines
    
def show_model_parameters(ax, model):
    """Show model parameters."""
    text = "gain = {:.2f}\ntau = {:.4f}s\nbleed = {:.2f}".format(model.gain.value, model.tau.value, model.integrator.value)
    ax.text(0.1, 0.1, text, va='bottom', ha='left', transform=ax.transAxes)
    
    
    