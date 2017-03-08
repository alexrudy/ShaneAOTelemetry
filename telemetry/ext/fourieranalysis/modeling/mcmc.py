# -*- coding: utf-8 -*-
"""
Objective functions for MCMC-fitting a transfer function.
"""
import numpy as np
import emcee
import corner
import astropy.units as u
from .model import TransferFunction

def lnprior(theta):
    """Prior probabilities"""
    tau, gain, integrator = theta
    if not (0.0 < tau and 0.0 < gain < 1.0 and integrator < 0.0):
        return -np.inf
    
    lp = 0.0
    
    # Gaussian around tau = 0.005
    lp += -np.power((0.005 - tau)/(2.0 * 0.1), 2)
    return lp
    

def lnlike(theta, x, y, rate, weights):
    """Likelihood for a transfer function."""
    tau, gain, integrator = theta
    model = np.log(TransferFunction.evaluate(x, tau, gain, integrator, rate))
    return - 0.5 * np.sum((y - model) ** 2 * weights)
    
def lnprob(theta, x, y, rate, weights):
    """Probability"""
    lp = lnprior(theta)
    if not np.isfinite(lp):
        return lp
    return lp + lnlike(theta, x, y, rate, weights)
    
def gauss_freq_weighting(freq):
    sig = np.max(freq)/2.0
    w = np.exp(-0.5 * (freq/sig)**2.0)
    return w
    
def fit_emcee(tf, index, nwalkers=100):
    """Fit emcee data to a transfer function."""
    m_init = TransferFunction.expected(tf)
    ndim = 3
    
    start = m_init.parameters[:3]
    pos = start[None,:] * np.random.randn(nwalkers,ndim) * 1e-3
    
    x = tf.frequencies.to(u.Hz).value
    w = gauss_freq_weighting(x)
    y = np.log(tf.data[:,index])
    
    sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob, args=(x, y, m_init.rate.value, w))
    sampler.run_mcmc(pos, 1000)
    
    samples = sampler.chain[:,100:,:].reshape((-1, ndim))
    return samples
    
def plot_emcee(samples, tf):
    """Plot an emcee fit."""
    m_init = TransferFunction.expected(tf)
    
    parameters = m_init.parameters[:3]
    samples[...,0] *= 1e3
    parameters[0] *= 1e3
    
    fig = corner.corner(samples, labels=[r"$\tau$", "$gain$", "$c$"], truths=parameters, quantiles=[0.5], show_titles=True)