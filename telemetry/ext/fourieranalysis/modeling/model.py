# -*- coding: utf-8 -*-
import astropy.units as u
from astropy.modeling import FittableModel, Parameter, fitting
from astropy.utils.console import ProgressBar
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
    """Compute the delay due to a stare."""
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

class IntegratorParameter(Parameter):
    """Integrator parameters are stored internally in log space from 1.0 """
    def __init__(self, *args, **kwargs):
        kwargs['getter'] = self._get
        kwargs['setter'] = self._set
        super(IntegratorParameter, self).__init__()
        
    def _get(self, value):
        """Return the value."""
        return 1.0 - np.exp(value)
        
    def _set(self, value):
        """Convert to log space."""
        return np.log(1.0 - value)

class TransferFunctionBase(FittableModel):
    """Basic features common to transfer functions."""
    
    inputs = ('freq',)
    outputs = ('y',)

class TransferFunction(FittableModel):
    """Model of a transfer function."""
    
    inputs = ('freq',)
    outputs = ('y',)
    
    tau = Parameter(min=0.0, max=5.0)
    gain = Parameter(min=0.0, max=1.0)
    ln_c = Parameter(min=-1e2, max=0.0)
    rate = Parameter(fixed=True)
    
    def __init__(self, *args, **kwargs):
        if 'integrator' in kwargs:
            kwargs.setdefault('ln_c', np.log(1.0 - kwargs.pop('integrator')))
        super(TransferFunction, self).__init__(*args, **kwargs)
    
    @property
    def integrator(self):
        """Return the integrator value."""
        return 1.0 - np.exp(self.ln_c.value)
        
    @integrator.setter
    def integrator(self, value):
        """Set the intergrator."""
        self.ln_c.value = np.log(1.0 - value)
    
    @classmethod
    def expected(cls, dataset):
        """Given an emperical transfer function, compute the expected model."""
        return cls(tau=1.0 + 900e-6 * dataset.rate, gain=dataset.gain, 
            ln_c=np.log(1.0 - dataset.bleed), rate=dataset.rate)
    
    @staticmethod
    def evaluate(freq, tau, gain, ln_c, rate):
        """Evaluate a transfer function."""
        freq = np.asarray(freq)
        
        integrator = 1.0 - np.exp(ln_c)
        
        hdw_cont = stare(freq, rate) # Stare averaging
        delay_cont = delay(freq, tau / rate) # Computational Delay
        
        # Delay total:
        #  Computation + WFS Stare + DM Stare
        delay_term = delay_cont * hdw_cont * hdw_cont
        
        # Integrating controller
        cofz = cofz_integrator(zinverse(freq, rate), gain, integrator)
        
        return np.abs(1.0 / (1.0 + delay_term * cofz) ** 2.0)
    

class JointTransferFunction(TransferFunctionBase):
    """Handle multi-mirror transfer functions."""
    
    tau = Parameter(min=0.1, max=5.0)
    tweeter_gain = Parameter(min=0.0, max=1.0)
    tweeter_ln_c = Parameter(min=-1e2, max=0.0)
    
    woofer_gain = Parameter(min=0.0, max=1.0)
    woofer_ln_c = Parameter(min=-1e2, max=0.0)
    woofer_tau = Parameter(min=0.1, max=5.0)
    woofer_alpha = Parameter(min=0.0, max=1.0)
    # woofer_beta = Parameter(min=0.0, max=1.0)
    
    woofer_overlap = Parameter(min=0.0, max=1.0, fixed=True)
    woofer_rate = Parameter(fixed=True)
    rate = Parameter(fixed=True)
    
    
    def __init__(self, *args, **kwargs):
        for mirror in ('tweeter', 'woofer'):
            if '{0}_integrator'.format(mirror) in kwargs:
                kwargs.setdefault('{0}_ln_c'.format(mirror), np.log(1.0 - kwargs.pop('{0}_integrator'.format(mirror))))
        super(JointTransferFunction, self).__init__(*args, **kwargs)
    
    @classmethod
    def expected(cls, dataset, overlap=1.0):
        """Given an emperical transfer function, compute the expected model."""
        info = dataset.instrument_data
        return cls(tau=1.0 + 900e-6 * info.wfs_rate, rate=info.wfs_rate,
                   tweeter_gain=info.tweeter_gain, tweeter_integrator=info.tweeter_bleed,
                   woofer_gain=info.woofer_gain, woofer_integrator=info.woofer_bleed,
                   woofer_tau=6.4e-3 * info.wfs_rate, woofer_alpha=info.alpha,
                   woofer_overlap=overlap, woofer_rate=info.woofer_rate)
    
    @property
    def tweeter_integrator(self):
        """Return the integrator value."""
        return 1.0 - np.exp(self.tweeter_ln_c.value)
        
    @tweeter_integrator.setter
    def tweeter_integrator(self, value):
        """Set the intergrator."""
        self.tweeter_ln_c.value = np.log(1.0 - value)
    
    @property
    def woofer_integrator(self):
        """Return the integrator value."""
        return 1.0 - np.exp(self.woofer_ln_c.value)
        
    @woofer_integrator.setter
    def woofer_integrator(self, value):
        """Set the intergrator."""
        self.woofer_ln_c.value = np.log(1.0 - value)
        
    @staticmethod
    def evaluate(freq, tau, tweeter_gain, tweeter_ln_c, woofer_gain, woofer_ln_c, woofer_tau, woofer_alpha, woofer_overlap, woofer_rate, rate):
        """Evaluate the dual method transfer function"""
        freq = np.asarray(freq)
        tweeter_integrator = 1.0 - np.exp(tweeter_ln_c)
        woofer_integrator = 1.0 - np.exp(woofer_ln_c)
        zinv_tweeter = zinverse(freq, rate)
        zinv_woofer = zinverse(freq, rate)

        wfs_stare = tweeter_stare = stare(freq, rate) # Stare averaging
        woofer_stare = stare(freq, woofer_rate)
        delay_rcomp = delay(freq, tau / rate) # Computational Delay
        delay_wcomp = delay(freq, woofer_tau / rate)

        # Delay total for tweeter:
        #  Computation + WFS Stare + DM Stare
        delay_tweeter = delay_rcomp * wfs_stare * tweeter_stare
        delay_woofer = delay_rcomp * wfs_stare * delay_wcomp * woofer_stare
        
        # Integrating controller for the tweeter
        cofz_tweeter = cofz_integrator(zinv_tweeter, tweeter_gain, tweeter_integrator)
        cofz_woofer = cofz_integrator(zinv_woofer, woofer_gain, woofer_integrator)
        
        # Temporal filter, which only has one step.
        filter_woofer = woofer_alpha * zinv_tweeter
        
        # Transfer functions:
        woofer_tf = np.power(1.0 / np.abs(1.0 + delay_woofer * cofz_woofer), 2.0)
        tweeter_tf = np.power(1.0 / np.abs(1.0 + delay_tweeter * cofz_tweeter), 2.0)
        joint_tf = np.power(1.0 / np.abs(1.0 + delay_woofer * cofz_woofer + delay_tweeter * cofz_tweeter * (1.0 - filter_woofer)), 2.0)
        
        return (woofer_overlap * joint_tf) + (1.0 - woofer_overlap) * tweeter_tf