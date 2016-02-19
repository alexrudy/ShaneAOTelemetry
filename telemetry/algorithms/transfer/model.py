# -*- coding: utf-8 -*-
import astropy.units as u
from astropy.modeling import FittableModel, Parameter, fitting
from astropy.utils.console import ProgressBar
import numpy as np

def log_frequency_weighting(freq):
    """Given an array of frequencies, compute the inverse-log-weighting."""
    lfreq = -np.log(np.abs(freq))
    lfreq[~np.isfinite(lfreq)] = 0.0
    lfw = lfreq - lfreq.min()
    lfwn = lfw/lfw.max()
    return lfwn

def expected_model(tf, tau=0.01):
    """Generate the expected model."""
    model = TransferFunction(tau=tau, gain=tf.sequence.gain, integrator=tf.sequence.tweeter_bleed, rate=tf.rate)
    return model

def fit_model(tf, tau=0.01, index=0):
    """docstring for fit_model"""
    model_init = expected_model(tf, tau)
    fitter = fitting.LevMarLSQFitter()
    y = tf.data[:,index]
    x = tf.frequencies.to(u.Hz).value
    model = fitter(model_init, x, y, weights=log_frequency_weighting(x))
    return model
    
def fit_all_models(tf, tau):
    """Fit all models."""
    template = np.ones_like(tf.data[0])
    model_result = TransferFunction(tau=template * tau, gain=template * tf.sequence.gain, 
        integrator=template * tf.sequence.tweeter_bleed, rate=tf.sequence.rate)
    model_init = expected_model(tf, tau)
    x = tf.frequencies.to(u.Hz).value
    fitter = fitting.LevMarLSQFitter()
    
    for i in ProgressBar(tf.data.shape[1]):
        y = tf.data[:,i]
        model = fitter(model_init, x, y, weights=log_frequency_weighting(x))
        model_result.tau[i] = model.tau.value
        model_result.gain[i] = model.gain.value
        model_result.integrator[i] = model.integrator.value
    return model_result

eps = np.finfo(np.float).eps

class TransferFunction(FittableModel):
    """Model of a transfer function."""
    
    inputs = ('freq',)
    outputs = ('y',)
    
    tau = Parameter(min=0.0)
    gain = Parameter(min=0.0, max=1.0 - eps)
    integrator = Parameter(min=eps, max=1.0 - eps)
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
        
        return np.abs(1.0 / (1.0 + delay_term * cofz) ** 2.0)
    