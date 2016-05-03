# -*- coding: utf-8 -*-
"""View tools for periodograms"""

import astropy.units as u
import numpy as np

from ..ext.fourieranalysis.utils import frequencies

def show_transferfunction(ax, tf, rate=1.0, **kwargs):
    """Similar to show_periodogram but with slightly different defaults.
    """
    lines = show_periodogram(ax, tf, rate=1.0, **kwargs)
    ax.set_ylabel("Error Transfer Function")
    return lines

def show_periodogram(ax, periodogram, rate=1.0, **kwargs):
    """Show a periodogram on an axis."""
    
    periodogram = np.asarray(periodogram)
    rate = u.Quantity(rate, u.Hz)
    lim = np.max(rate).value / 2.0
    
    if periodogram.ndim != 1:
        kwargs.setdefault('alpha', 0.1)
    kwargs.setdefault('color', 'b')
    
    length = periodogram.shape[0]
    freq = frequencies(length, rate)
    lines = ax.plot(np.asarray(freq), periodogram, **kwargs)
    ax.set_xlabel("Frequency ({})".format(rate.unit))
    ax.set_ylabel("Power")
    ax.set_xscale("symlog")
    ax.set_yscale("log")
    ax.set_xlim(-lim, lim)
    return lines
    
def show_model_parameters(ax, model, name="Model", pos=(0.1, 0.1)):
    """Show model parameters."""
    text = r"{:s}\n$\mathrm{{gain}} = {:.4f}$\n$\tau ={:.4f}\mathrm{{s}}$\n$\mathrm{{bleed}} = {:.3f}$".format(name, model.gain.value, model.tau.value, model.integrator)
    t = text.split(r"\n")
    x, y = pos
    ax.text(x, y, "\n".join(t), va='bottom', ha='left', transform=ax.transAxes, bbox=dict(fc='white', ec='black'))
    
    
    