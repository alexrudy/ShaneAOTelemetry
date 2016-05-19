# -*- coding: utf-8 -*-

import os
import numpy as np
from telemetry.utils import makedirs
from .utils import frequencies
import astropy.units as u
from .modeling.model import TransferFunction as TransferFunctionModel
from .modeling.linfit import apply_LevMarLSQFitter
from telemetry.views.core import telemetry_plotting_task
from celery.utils.log import get_task_logger

log = get_task_logger(__name__)

def show_periodogram(ax, periodogram, rate=1.0, **kwargs):
    """Show a periodogram on an axis."""
    
    periodogram = np.asarray(periodogram)
    rate = u.Quantity(rate, u.Hz)
    lim = np.max(rate).value / 2.0
    
    if periodogram.ndim != 1:
        kwargs.setdefault('alpha', 0.1)
        periodogram = periodogram.reshape(periodogram.shape[0], -1)
        
    kwargs.setdefault('color', 'b')
    
    length = periodogram.shape[0]
    freq = frequencies(length, rate)
    lines = ax.plot(np.asarray(freq), periodogram, **kwargs)
    ax.set_xlabel("Frequency ({})".format(rate.unit))
    ax.set_ylabel("Power")
    ax.set_xscale("symlog")
    ax.set_yscale("log")
    ax.set_xlim(-lim, lim)
    return lines

@telemetry_plotting_task(category='periodogram')
def periodogram_plot(ax, periodogram, **kwargs):
    """Plot a periodogram."""
    data = periodogram.read()
    length = data.shape[-1]
    data = data.reshape((-1, length))
    show_periodogram(ax, data.T, rate=periodogram.dataset.rate, color='k')
    ax.set_title('{0:s} Periodogram for s{1:04d} ({2:s})'.format(periodogram.kind.kind.capitalize(), periodogram.dataset.sequence, periodogram.dataset.gaintext))
    if np.min(data) < 1e-10:
        ax.set_ylim(np.min(data[data > 1e-10]), np.max(data))
    
def plot_mean_transfer_model(transfer_model, ax):
    """Plot the fit of a transfer function."""
    model = transfer_model.read()
    fit_model = TransferFunctionModel(tau=model.tau.value.mean(), 
        ln_c=model.ln_c.value.mean(), gain=model.gain.value.mean(), 
        rate=model.rate.value.mean())
    freq = frequencies(length, model.rate.mean())
    data_f = fit_model(freq)
    show_periodogram(ax, data_f, rate=transfer.dataset.instrument_data.wfs_rate, color='g', label='Fit Model')
    show_model_parameters(ax, fit_model, pos=(0.8, 0.1))

def plot_fit_transfer_model(model, freq, data, ax):
    """From a transfer function, """
    fit_model = apply_LevMarLSQFitter(model, freq, data)
    data_f = fit_model(freq)
    show_periodogram(ax, data_f, rate=model.rate, color='g', label='Fit Model')
    show_model_parameters(ax, fit_model, pos=(0.8, 0.1))

@telemetry_plotting_task(category='transferfunction')
def transferfunction_plot(ax, transfer):
    """Plot a periodogram."""
    data = transfer.read()
    length = data.shape[-1]
    freq = frequencies(length, transfer.dataset.rate)
    
    data_p = transfer.kind.normalized(data)
    data_m = transfer.kind.logaverage(data)
    
    alpha = max([1.0 / float(np.prod(data_p.shape[:-1])), 0.005])
    
    expected_model = TransferFunctionModel.expected(transfer.dataset)
    data_e = expected_model(freq)
    
    show_periodogram(ax, data_p.T, rate=transfer.dataset.instrument_data.wfs_rate, color='b', alpha=alpha)
    show_periodogram(ax, data_m.T, rate=transfer.dataset.instrument_data.wfs_rate, color='b', label="Data")
    show_periodogram(ax, data_e, rate=transfer.dataset.instrument_data.wfs_rate, color='r', label='Expected Model')
    show_model_parameters(ax, expected_model, pos=(0.6, 0.1), name="Expected")
    
    if "transferfunctionmodel/{0}".format(transfer.kind) in transfer.dataset.telemetry:
        log.info("Using transfer function model fit from data.")
        transfer_model = transfer.dataset.telemetry["transferfunctionmodel/{0}".format(transfer.kind)]
        plot_mean_transfer_model(transfer_model, ax)
    else:
        log.info("Generating transfer function model fit.")
        plot_fit_transfer_model(expected_model, freq, data_m, ax)
    
    ax.set_title('{0:s} ETF for s{1:04d} "{2:s}"'.format(transfer.kind.kind.capitalize(), transfer.dataset.sequence, transfer.dataset.instrument_data.loop))
    ax.legend(loc='best')
    ax.text(0.0, 1.01, r"${:.0f}\mathrm{{Hz}}$ $\alpha={:.3f}$".format(transfer.dataset.instrument_data.wfs_rate, transfer.dataset.instrument_data.alpha), transform=ax.transAxes)

@telemetry_plotting_task(category='transferfunctionmodel')
def transferfunction_model_summary(ax, telemetry, **kwargs):
    """Plot a model summary"""
    model = telemetry.read()
    parameter = kwargs.pop('parameter', 'gain')
    data = getattr(model, parameter).value
    if data.ndim == 2:
        model_summary_2d(ax, data, telemetry, parameter.capitalize(), **kwargs)
    else:
        model_summary_1d(ax, data.flatten(), telemetry, parameter.capitalize(), **kwargs)
    
def model_summary_2d(ax, data, telemetry, name, **kwargs):
    """2D summary of model data."""
    kwargs.setdefault('cmap', 'viridis')
    im = ax.imshow(data, **kwargs)
    ax.figure.colorbar(im, ax=ax)
    ax.grid(False)
    ax.set_title("Fit {0} for {1} {2}".format(name, telemetry.kind.kind.capitalize(), telemetry.dataset.title()))
    
def model_summary_1d(ax, data, telemetry, name, **kwargs):
    """Model summary in 1 dimension."""
    mode_n = np.arange(data.shape[0])
    image = ax.bar(mode_n, data, **kwargs)
    ax.set_title("Fit {0} for {1} {2}".format(name, telemetry.kind.kind.capitalize(), telemetry.dataset.title()))
    ax.set_xlim(0, data.shape[0] + 1)

def show_model_parameters(ax, model, name="Model", pos=(0.1, 0.1)):
    """Show model parameters."""
    text = r"{:s}\n$\mathrm{{gain}} = {:.4f}$\n$\tau ={:.4f}\mathrm{{s}}$\n$\mathrm{{bleed}} = {:.3f}$".format(name, model.gain.value, model.tau.value, model.integrator)
    t = text.split(r"\n")
    x, y = pos
    ax.text(x, y, "\n".join(t), va='bottom', ha='left', transform=ax.transAxes, bbox=dict(fc='white', ec='black'))