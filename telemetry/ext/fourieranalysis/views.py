# -*- coding: utf-8 -*-

import os
import numpy as np
from telemetry.utils import makedirs
from .utils import frequencies
from .modeling.model import TransferFunction as TransferFunctionModel
from .modeling.linfit import apply_LevMarLSQFitter
from telemetry.views.periodogram import show_periodogram, show_model_parameters

def save_transfer_plot(transfer):
    """Save a plot of a transfer function."""
    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    plot_transfer_object(transfer, ax)
    filename = os.path.join(transfer.dataset.path, 
        "figures", "transfer",
        "s{0:04d}.tf.{1:s}.png".format(transfer.dataset.sequence, transfer.kind.kind))
    makedirs(os.path.dirname(filename))
    fig.savefig(filename)
    plt.close(fig)
    return filename
    
def save_periodogram_plot(periodogram):
    """Plot a periodogram."""
    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    filename = os.path.join(periodogram.dataset.path,"figures", "periodogram", "s{0:04d}.periodogram.{1:s}.png".format(periodogram.dataset.sequence, periodogram.kind.kind))
    makedirs(os.path.dirname(filename))
    data = periodogram.read()
    length = data.shape[-1]
    data = data.reshape((-1, length))
    show_periodogram(ax, data.T, rate=periodogram.dataset.wfs_rate)
    ax.set_title('{0:s} Periodogram for s{1:04d} ({2:s})'.format(periodogram.kind.kind.capitalize(), periodogram.dataset.sequence, periodogram.dataset.loop))
    fig.savefig(filename)
    plt.close(fig)
    return filename
    
def plot_mean_transfer_model(transfer_model, ax):
    """Plot the fit of a transfer function."""
    model = transfer_model.read()
    fit_model = TransferFunctionModel(tau=model.tau.value.mean(), 
        ln_c=model.ln_c.value.mean(), gain=model.gain.value.mean(), 
        rate=model.rate.value.mean())
    freq = frequencies(length, model.rate.mean())
    data_f = fit_model(freq)
    show_periodogram(ax, data_f, rate=transfer.dataset.wfs_rate, color='g', label='Fit Model')
    show_model_parameters(ax, fit_model, pos=(0.8, 0.1))

def plot_fit_transfer_model(model, freq, data, ax):
    """From a transfer function, """
    fit_model = apply_LevMarLSQFitter(model, freq, data)
    data_f = fit_model(freq)
    show_periodogram(ax, data_f, rate=model.rate, color='g', label='Fit Model')
    show_model_parameters(ax, fit_model, pos=(0.8, 0.1))

def plot_transfer_object(transfer, ax):
    """Plot a periodogram."""
    data = transfer.read()
    length = data.shape[-1]
    freq = frequencies(length, transfer.dataset.wfs_rate)
    weights = np.abs(frequencies(length, 1.0).value)
    data_p = data.T.reshape((length, -1))
    data_p /= data_p[weights >= (2.0/3.0) * np.max(weights)].mean(axis=0)[None,:]
    data_m = np.exp(np.log(data_p).mean(axis=1))
    alpha = 1.0 / float(data_p.shape[1])
    
    expected_model = TransferFunctionModel.expected(transfer.dataset)
    data_e = expected_model(freq)
    
    show_periodogram(ax, data_p, rate=transfer.dataset.wfs_rate, color='b', alpha=alpha)
    show_periodogram(ax, data_m, rate=transfer.dataset.wfs_rate, color='b', label="Data")
    show_periodogram(ax, data_e, rate=transfer.dataset.wfs_rate, color='r', label='Expected Model')
    show_model_parameters(ax, expected_model, pos=(0.6, 0.1), name="Expected")
    
    if "transferfunctionmodel/{0}".format(transfer.kind) in transfer.dataset.telemetry:
        transfer_model = transfer.dataset.telemetry["transferfunctionmodel/{0}".format(transfer.kind)]
        plot_mean_transfer_model(transfer_model, ax)
    else:
        plot_fit_transfer_model(expected_model, freq, data_m, ax)
    
    ax.set_title('{0:s} ETF for s{1:04d} "{2:s}"'.format(transfer.kind.kind.capitalize(), transfer.dataset.sequence, transfer.dataset.loop))
    ax.legend(loc='best')
    ax.text(0.0, 1.01, r"${:.0f}\mathrm{{Hz}}$ $\alpha={:.3f}$".format(transfer.dataset.wfs_rate, transfer.dataset.alpha), transform=ax.transAxes)
