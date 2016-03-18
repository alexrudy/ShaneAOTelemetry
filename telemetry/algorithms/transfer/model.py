# -*- coding: utf-8 -*-
import astropy.units as u
from astropy.modeling import FittableModel, Parameter, fitting
from astropy.utils.console import ProgressBar
import numpy as np

class TransferFunction(FittableModel):
    """Model of a transfer function."""
    
    inputs = ('freq',)
    outputs = ('y',)
    
    tau = Parameter(min=0.0)
    gain = Parameter(min=0.0, max=1.0)
    integrator = Parameter(min=1e-5, max=1.0 - 1e-3)
    rate = Parameter(fixed=True)
    
    @classmethod
    def expected(cls, transfer_function):
        """Given an emperical transfer function, compute the expected model."""
        return cls(tau=1.0/transfer_function.rate, gain=transfer_function.sequence.gain, 
            integrator=transfer_function.sequence.tweeter_bleed, rate=transfer_function.rate)
    
    @staticmethod
    def evaluate(freq, tau, gain, integrator, rate):
        """Evaluate a transfer function."""
        
        s = 1j * 2.0 * np.pi * freq
        bigT = 1.0 / rate
        
        sz = (s == 0)
        denom = (bigT * s)
        
        denom[sz] = 1.0
        
        hdw_cont = (1.0 - np.exp(-(bigT * s))) / denom
        hdw_cont[sz] = 1.0
        
        delay_cont = np.exp(-1.0 * tau * s)
        delay_term = delay_cont * hdw_cont * hdw_cont
        
        zinv = np.exp(-1.0 * bigT * s)
        cofz = gain / (1.0 - integrator * zinv)
        
        return np.log(np.abs(1.0 / (1.0 + delay_term * cofz) ** 2.0))
    