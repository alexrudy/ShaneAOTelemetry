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
        
    # kwargs.setdefault('color', 'b')
    
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
    ax.set_title('{0:s} Periodogram for {1:s}'.format(periodogram.kind.kind.capitalize(), periodogram.dataset.title()))
    if np.min(data) < 1e-10:
        ax.set_ylim(np.min(data[data > 1e-10]), np.max(data))
    
@telemetry_plotting_task(category='powerspectrum')
def powerspectrum_plot(ax, periodogram, **kwargs):
    """Plot the power-spectrum on a log-log scale."""
    data = periodogram.read()
    length = data.shape[-1]
    data = data.reshape((-1, length))
    show_periodogram(ax, data.T, rate=periodogram.dataset.rate, color='k', alpha=0.05)
    datam = data.mean(axis=0)
    show_periodogram(ax, datam, rate=periodogram.dataset.rate, color='k', label=r"$\mathrm{{{}}}$".format(periodogram.kind.kind.capitalize()))
    show_periodogram(ax, datam, rate=periodogram.dataset.rate, label=r"$|\mathrm{{{}}}|$".format(periodogram.kind.kind.capitalize()))
    freq = frequencies(length, u.Quantity(periodogram.dataset.rate, u.Hz))
    peg_idx = np.argmin(np.abs(freq - 5.0 * u.Hz))
    peg_freq = freq[peg_idx]
    peg_amp = datam[peg_idx]
    p_denom = 5.0
    ax.plot(freq, peg_amp * (freq.value / peg_freq.value) ** (-p_denom/3.0), label=r"$\propto f^{{-{:.0f}/3}}$".format(p_denom))
    
    ax.legend(loc='best')
    ax.set_title('{0:s} Power Spectrum for {1:s}'.format(periodogram.kind.kind.capitalize(), periodogram.dataset.title()))
    ax.set_xscale('log')
    ax.set_xlim(periodogram.dataset.rate / (2.0 * length), periodogram.dataset.rate / 2.0)
    if np.min(data) < 1e-10:
        ax.set_ylim(np.min(data[data > 1e-10]), np.max(data))
    
def plot_mean_transfer_model(transfer_model, ax, length):
    """Plot the fit of a transfer function."""
    model = transfer_model.read()
    fit_model = TransferFunctionModel(tau=model.tau.value.mean(), 
        ln_c=model.ln_c.value.mean(), gain=model.gain.value.mean(), 
        rate=model.rate.value.mean())
    freq = frequencies(length, model.rate.value.mean())
    data_f = fit_model(freq)
    show_periodogram(ax, data_f, rate=transfer_model.dataset.rate, color='g', label='Fit Model')
    show_model_parameters(ax, fit_model, pos=(0.8, 0.1))

def plot_fit_transfer_model(model, freq, data, ax):
    """From a transfer function, """
    fit_model = apply_LevMarLSQFitter(model, freq, data)
    data_f = fit_model(freq)
    show_periodogram(ax, data_f, rate=model.rate, label='Fit Model')
    show_model_parameters(ax, fit_model, pos=(0.8, 0.1))

@telemetry_plotting_task(category='transferfunction')
def transferfunction_plot(ax, transfer):
    """Plot a periodogram."""
    data = transfer.read()
    transferfunction_plot_from_data(ax, data, transfer)
    
def transferfunction_plot_from_data(ax, data, transfer, force_fit=False, show_fit=True):
    """Make a transfer function plot, with the data specified"""
    length = data.shape[-1]
    freq = frequencies(length, transfer.dataset.rate)
    
    data_p = transfer.kind.normalized(data)
    data_m = transfer.kind.logaverage(data)
    
    alpha = max([2.0 / float(np.prod(data_p.shape[:-1])), 0.005])
    
    expected_model = TransferFunctionModel.expected(transfer.dataset)
    data_e = expected_model(freq)
    
    lines = show_periodogram(ax, data_p.T, rate=transfer.dataset.instrument_data.wfs_rate, alpha=alpha, color='k')
    show_periodogram(ax, data_m.T, rate=transfer.dataset.instrument_data.wfs_rate, color=lines[0].get_color(), label="Data")
    show_periodogram(ax, data_e, rate=transfer.dataset.instrument_data.wfs_rate, label='Expected Model')
    show_model_parameters(ax, expected_model, pos=(0.6, 0.1), name="Expected")
    if show_fit:
        if "transferfunctionmodel/{0}".format(transfer.kind.kind) in transfer.dataset.telemetry and (not force_fit):
            log.info("Using transfer function model fit from data.")
            transfer_model = transfer.dataset.telemetry["transferfunctionmodel/{0}".format(transfer.kind.kind)]
            plot_mean_transfer_model(transfer_model, ax, length=length)
        else:
            log.info("Generating transfer function model fit.")
            plot_fit_transfer_model(expected_model, freq, data_m, ax)
    
    ax.set_title('{0:s} ETF for {1:s}'.format(transfer.kind.kind.capitalize(), transfer.dataset.title()))
    ax.legend(loc='best')
    ax.text(0.0, 0.99, 
        r"$\alpha={:.3f}$".format(transfer.dataset.instrument_data.alpha), 
        transform=ax.transAxes, va='top')

@telemetry_plotting_task(category='tflowmodes')
def tf_low_modes(ax, telemetry):
    """Plot transfer function for low modes."""
    data = telemetry.read()
    transferfunction_plot_from_data(ax, data[:20], telemetry, show_fit=True)
    data_m = telemetry.kind.logaverage(data)
    show_periodogram(ax, data_m.T, rate=telemetry.dataset.instrument_data.wfs_rate, color='m', label="All Modes")
    
    ax.set_title('Limited {0:s} ETF for {1:s}'.format(telemetry.kind.kind.capitalize(), telemetry.dataset.title()))
    ax.legend(loc='best')
    

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