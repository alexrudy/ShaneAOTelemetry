# -*- coding: utf-8 -*-
import astropy.units as u
from astropy.modeling import FittableModel, Parameter, fitting
from astropy.utils.console import ProgressBar
import numpy as np
from .model import TransferFunction

class LogLevMarLSQFitter(fitting.LevMarLSQFitter):
    """A LevMarLSQ fitter which operates in log space."""
    
    def objective_function(self, fps, *args):
        """
        Function to minimize.

        Parameters
        ----------
        fps : list
            parameters returned by the fitter
        args : list
            [model, [weights], [input coordinates]]
        """

        model = args[0]
        weights = args[1]
        fitting._fitter_to_model_params(model, fps)
        meas = args[-1]
        if weights is None:
            return np.ravel(np.log(model(*args[2 : -1])) - np.log(meas))
        else:
            return np.ravel(np.log(weights * (model(*args[2 : -1])) - np.log(meas)))
    

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
    model = TransferFunction.expected(tf.dataset)
    return model

def fit_model(tf, y, index=0):
    """Fit a model to a transfer function."""
    model_init = expected_model(tf)
    x = tf.frequencies.to(u.Hz).value
    model = apply_LevMarLSQFitter(model_init, x, y)
    return model
    
    
def apply_LevMarLSQFitter(m, x, y):
    """Apply the LMLSQ Fitter"""
    f = LogLevMarLSQFitter()
    model = f(m, x, y, maxiter=1000)
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