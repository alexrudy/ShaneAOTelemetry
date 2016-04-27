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
    ln_c = Parameter(min=-1e2, max=0.0)
    rate = Parameter(fixed=True)
    
    @property
    def integrator(self):
        """Return the integrator value."""
        return 1.0 - np.exp(self.ln_c.value)
        
    @integrator.setter
    def set_integrator(self, value):
        """Set the intergrator."""
        self.ln_c.value = np.log(1.0 - value)
    
    @classmethod
    def expected(cls, dataset):
        """Given an emperical transfer function, compute the expected model."""
        return cls(tau=(1.0/dataset.wfs_rate) + 900e-6, gain=dataset.gain, 
            ln_c=np.log(1.0 - dataset.tweeter_bleed), rate=dataset.wfs_rate)
    
    @staticmethod
    def evaluate(freq, tau, gain, ln_c, rate):
        """Evaluate a transfer function."""
        freq = np.asarray(freq)
        
        integrator = 1.0 - np.exp(ln_c)
        
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
        
        return np.abs(1.0 / (1.0 + delay_term * cofz) ** 2.0)
    