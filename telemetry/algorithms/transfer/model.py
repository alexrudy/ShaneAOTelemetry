# -*- coding: utf-8 -*-
import astropy.units as u
from astropy.modeling import FittableModel, Parameter, fitting
from astropy.utils.console import ProgressBar
import numpy as np

def log_frequency_weighting(freq):
    """Given an array of frequencies, compute the inverse-log-weighting."""
    # freq[freq != 0.0] = np.nan
    lfreq = -np.log(np.abs(freq))
    lfreq[~np.isfinite(lfreq)] = 0.0
    lfw = lfreq - lfreq.min()
    lfwn = lfw/lfw.max()
    lfwn[freq == 0.0] = 1.0
    return lfwn
    
def gauss_freq_weighting(freq):
    sig = np.max(freq)/2.0
    w = np.exp(-0.5 * (freq/sig)**2.0)
    return w

def expected_model(tf):
    """Generate the expected model."""
    model = TransferFunction(tau=1.0/tf.rate, gain=tf.sequence.gain, integrator=tf.sequence.tweeter_bleed, rate=tf.rate)
    return model

def fit_model(tf, index=0):
    """docstring for fit_model"""
    model_init = expected_model(tf)
    fitter = fitting.LevMarLSQFitter()
    y = tf.data[:,index]
    x = tf.frequencies.to(u.Hz).value
    model = apply_fitter(fitter, model_init, x, y)
    return model
    
    
def apply_fitter(f, m, x, y):
    """Apply the LMLSQ Fitter"""
    ly = np.log(y)
    model = f(m, x, ly, weights=gauss_freq_weighting(x), maxiter=1000)
    if f.fit_info['ierr'] not in [1, 2, 3, 4]:
        print("Fit may not have converged. {0}".format(f.fit_info['message']))
    return model
    

def fit_all_models(tf):
    """Fit all models."""
    template = np.ones_like(tf.data[0])
    model_result = TransferFunction(tau=template / tf.rate, gain=template * tf.sequence.gain, 
        integrator=template * tf.sequence.tweeter_bleed, rate=tf.sequence.rate)
    model_init = expected_model(tf)
    x = tf.frequencies.to(u.Hz).value
    fitter = fitting.LevMarLSQFitter()
    
    for i in ProgressBar(tf.data.shape[1]):
        y = tf.data[:,i]
        model = apply_fitter(fitter, model_init, x, y)
        model_result.tau[i] = model.tau.value
        model_result.gain[i] = model.gain.value
        model_result.integrator[i] = model.integrator.value
    return model_result

class TransferFunction(FittableModel):
    """Model of a transfer function."""
    
    inputs = ('freq',)
    outputs = ('y',)
    
    tau = Parameter(min=0.0)
    gain = Parameter(min=0.0, max=1.0)
    integrator = Parameter(min=1e-5, max=1.0 - 1e-3)
    rate = Parameter(fixed=True)
    
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
    