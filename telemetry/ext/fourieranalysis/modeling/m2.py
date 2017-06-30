# -*- coding: utf-8 -*-
"""
M2 is a quick decomposition of ETF modeling.
"""

import astropy.units as u
from astropy.modeling import FittableModel, Model, Parameter, models
import numpy as np

def zinverse(freq, rate):
    """z^-1 for some data"""
    s = 1j * 2.0 * np.pi * freq
    T = 1.0 / rate
    return np.exp(-1.0 * T * s)

def cofz_integrator(zinv, gain, integrator):
    """Compute C(z) for an integrator."""
    cofz = gain / (1.0 - integrator * zinv)
    return cofz
    
def stare(freq, rate):
    """Compute the averaging due to a stare for a single frame."""
    s = 1j * 2.0 * np.pi * freq
    T = 1.0 / rate
    denom = (T * s)
    denom[(s == 0)] = 1.0
    hdw_cont = (1.0 - zinverse(freq, rate)) / denom
    hdw_cont[(s == 0)] = 1.0
    return hdw_cont
    
def delay(freq, tau):
    """Tau-based delay"""
    s = 1j * 2.0 * np.pi * freq
    return np.exp(-1.0 * tau * s)

def _bleed_get(value):
    """Return the value."""
    return 1.0 - np.exp(value)
    
def _bleed_set(value):
    """Convert to log space."""
    return np.log(1.0 - value)


class ErrorTransferFunction(FittableModel):
    """A core model component which converts C(z) to an ETF."""
    
    inputs = ('cofz',)
    outputs = ('y',)
    
    @staticmethod
    def evaluate(cofz):
        """Convert a modularly constructed C(z) to an ETF"""
        return np.abs(1.0 / (1.0 + cofz) ** 2.0)

class Delay(FittableModel):
    """Delay for standard hardware."""
    inputs = ('freq',)
    outputs = ('y',)
    
    tau = Parameter(min=0.0, max=5.0)
    rate = Parameter(fixed=True)
    
    @staticmethod
    def evaluate(freq, tau, rate):
        """Evaluate a transfer function."""
        freq = np.asarray(freq)
        
        hdw_cont = stare(freq, rate) # Stare averaging
        delay_cont = delay(freq, tau / rate) # Computational Delay
        
        # Delay total:
        #  Computation + WFS Stare + DM Stare
        delay_term = delay_cont * hdw_cont * hdw_cont
        return delay_term
    
class Integrator(FittableModel):
    """A standard integrator"""
    inputs = ('freq',)
    outputs = ('y',)
    
    gain = Parameter(min=0.0, max=1.0)
    bleed = Parameter(max=-1e-2, getter=_bleed_get, setter=_bleed_set)
    
    rate = Parameter(fixed=True)
    
    @staticmethod
    def evaluate(freq, gain, bleed, rate):
        """Evaluate a transfer function."""
        return cofz_integrator(zinverse(freq, rate), gain, 1.0 - np.exp(bleed))

    
class Filtered(FittableModel):
    """A filtered mirror model"""
    
    inputs = ('freq','cofz')
    outputs = ('y',)
    
    alpha = Parameter(min=0.0, max=1.0)
    bleed = Parameter(max=-1e-2, getter=_bleed_get, setter=_bleed_set)
    
    rate = Parameter(fixed=True)
    
    @staticmethod
    def evaluate(freq, cofz, alpha, bleed, rate):
        """Evaluate the dual method transfer function"""
        zinv = zinverse(freq, rate)
        return cofz / (1.0 - cofz_integrator(zinv, 1.0-alpha, 1.0 - np.exp(bleed)))
    
    def applied(self, cofz):
        """Return the appropriate compound model to apply this filter."""
        return (models.Mapping((0,0)) | (models.Identity(1) & cofz) | self)


class FlexibleKalmanFilter(FittableModel):
    """A model of a Kalman filter"""
    
    inputs = ('freq',)
    outputs = ('y',)
    
    gain = Parameter(min=0.0, max=1.0)
    alpha = Parameter(max=-1e-2, getter=_bleed_get, setter=_bleed_set)
    hpcoeff = Parameter(max=-1e-2, getter=_bleed_get, setter=_bleed_set)
    rate = Parameter(fixed=True)
    
    @staticmethod
    def evaluate(freq, gain, alpha, hpcoeff, rate):
        """Evaluate the Kalman Filter"""
        zinv = zinverse(freq, rate)
        cofz = gain / (1.0 - (1.0 - np.exp(alpha)) * zinv)
        cofz *= 1.0 / (1.0 + (1.0 - np.exp(hpcoeff)) * zinv)
        return cofz
        

class KalmanFilter(FittableModel):
    """A model of a Kalman filter"""
    
    inputs = ('freq',)
    outputs = ('y',)
    
    k1 = Parameter(min=0.0, max=1.0)
    alpha = Parameter(max=-1e-2, getter=_bleed_get, setter=_bleed_set)
    rate = Parameter(fixed=True)
    
    @staticmethod
    def evaluate(freq, k1, alpha, rate):
        """Evaluate the Kalman Filter"""
        zinv = zinverse(freq, rate)
        a =  (1.0 - np.exp(alpha))
        cofz = (a * k1) / (1.0 - a * zinv)
        cofz *= 1.0 / (1.0 + k1 * zinv)
        return cofz
        