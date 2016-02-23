# -*- coding: utf-8 -*-
"""View tools for periodograms"""

import astropy.units as u
import numpy as np

from ..models.periodogram import frequencies

def show_periodogram(ax, periodogram, rate=1.0, **kwargs):
    """Show a periodogram on an axis."""
    rate = u.Quantity(rate, u.Hz)
    
    lim = np.max(rate).value / 2.0
    
    kwargs.setdefault('alpha', 0.1)
    kwargs.setdefault('color', 'b')
    length = periodogram.shape[0]
    lines = ax.plot(frequencies(length, rate).value, periodogram, **kwargs)
    ax.set_xlabel("Frequency ({})".format(rate.unit))
    ax.set_xscale("symlog")
    ax.set_yscale("log")
    ax.set_xlim(-lim, lim)
    return lines
    
def show_model_parameters(ax, model, name="Model", pos=(0.1, 0.1)):
    """Show model parameters."""
    text = "{:s}\n gain = {:.2f}\ntau = {:.4f}s\nbleed = {:.3f}".format(name, model.gain.value, model.tau.value, model.integrator.value)
    x, y = pos
    ax.text(x, y, text, va='bottom', ha='left', transform=ax.transAxes, bbox=dict(fc='white', ec='black'))
    
    
    