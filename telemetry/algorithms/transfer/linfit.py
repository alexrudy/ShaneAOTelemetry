# -*- coding: utf-8 -*-
import astropy.units as u
from astropy.modeling import FittableModel, Parameter, fitting
from astropy.utils.console import ProgressBar
import numpy as np
from .model import TransferFunction

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
    if index is not None:
        y = tf.data[:,index]
    else:
        y = tf.data.mean(axis=1)
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
    
    for i in range(tf.data.shape[1]):
        y = tf.data[:,i]
        model = apply_fitter(fitter, model_init, x, y)
        model_result.tau[i] = model.tau.value
        model_result.gain[i] = model.gain.value
        model_result.integrator[i] = model.integrator.value
    return model_result