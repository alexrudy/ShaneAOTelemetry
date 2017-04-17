# -*- coding: utf-8 -*-
import astropy.units as u
from astropy.modeling import FittableModel, Parameter, fitting
from astropy.utils.console import ProgressBar
import numpy as np
from .model import TransferFunction
from ..utils import frequencies

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
            return np.ravel(np.log(weights * model(*args[2 : -1])) - np.log(meas))
    

def frequency_weigts_suppress_static(freq):
    """Suppress static values in frequency weights."""
    x = np.asarray(freq)
    g = np.exp(-0.5 * (x**2.0) / (0.1))
    g /= g.max()
    g[g==1.0] = 1.0 - 1e-5
    g[x==0.0] = 1.0 - 1e-5
    return (1.0 - g)

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
    
    
def apply_LevMarLSQFitter(m, x, y, w=None):
    """Apply the LMLSQ Fitter"""
    f = LogLevMarLSQFitter()
    if w is None:
        w = frequency_weigts_suppress_static(x)
    model = f(m, x, y, weights=w, maxiter=3000)
    if f.fit_info['ierr'] not in [1, 2, 3, 4]:
        print("Fit may not have converged. {0}".format(f.fit_info['message']))
    return model
    

def fit_models(tf, cls, progressbar=False):
    """Fit all models."""
    data = tf.read()
    template = np.ones(data.shape[:-1], dtype=np.float)
    model_init = cls.expected(tf.dataset)
    attrs = {}
    for param_name in model_init.param_names:
        attrs[param_name] = getattr(model_init, param_name).value * template
    model_result = cls(**attrs)
    
    x = frequencies(data.shape[-1], model_init.rate)
    fitter = fitting.LevMarLSQFitter()
    
    data.shape = (-1, data.shape[-1])
    
    if progressbar:
        iterator = ProgressBar(data.shape[0])
    else:
        iterator = range(data.shape[0])
    
    for i in iterator:
        y = data[i,:]
        model = apply_LevMarLSQFitter(model_init, x, y)
        for param_name in model.param_names:
            getattr(model_result, param_name).value.flat[i] = getattr(model, param_name).value
    for param_name in model.param_names:
        print("{0}: {1}".format(param_name, getattr(model_result, param_name).value.mean()))
    return model_result