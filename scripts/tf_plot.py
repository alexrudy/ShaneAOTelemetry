#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
import os
import astropy.units as u
from telemetry.cli import parser
from telemetry import makedirs
from telemetry.models import Telemetry, TelemetryKind, Dataset, TransferFunction, frequencies
from telemetry.algorithms.transfer.model import TransferFunction as TransferFunctionModel
from telemetry.algorithms.transfer.linfit import apply_LevMarLSQFitter
from telemetry.views.periodogram import show_periodogram, show_model_parameters
from astropy.utils.console import ProgressBar

import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams['text.usetex'] = False


def setup(parser):
    """Set up the argument parser"""
    parser.add_argument("kind", type=str, help="Data kind to periodogram.")

def plot_transfer(transfer, ax):
    """Plot a periodogram."""
    filename = os.path.join(transfer.dataset.path,"figures", "transfer", "s{0:04d}.tf.{1:s}.png".format(transfer.dataset.sequence, transfer.kind.kind))
    makedirs(os.path.dirname(filename))
    
    data = transfer.read()
    
    expected_model = TransferFunctionModel.expected(transfer.dataset)
    length = data.shape[-1]
    freq = frequencies(length, expected_model.rate)
    data_e = expected_model(freq)
    
    data_p = data.T.reshape((length, -1))
    data_p /= data_p[np.abs(freq) > 100 * u.Hz].mean(axis=0)[None,:]
    data_m = np.exp(np.log(data_p).mean(axis=1))
    fit_model = apply_LevMarLSQFitter(expected_model, freq, data_m)
    data_f = fit_model(freq)
    
    alpha = 1.0 / float(data_p.shape[1])
    
    show_periodogram(ax, data_p, rate=transfer.dataset.wfs_rate, color='b', alpha=alpha)
    show_periodogram(ax, data_m, rate=transfer.dataset.wfs_rate, color='b', label="Data")
    
    
    show_periodogram(ax, data_e, rate=transfer.dataset.wfs_rate, color='r', label='Expected Model')
    show_periodogram(ax, data_f, rate=transfer.dataset.wfs_rate, color='g', label='Fit Model')
    
    show_model_parameters(ax, expected_model, pos=(0.6, 0.1), name="Expected")
    show_model_parameters(ax, fit_model, pos=(0.8, 0.1))
    
    
    ax.set_title('{0:s} ETF for s{1:04d} "{2:s}"'.format(transfer.kind.kind.capitalize(), transfer.dataset.sequence, transfer.dataset.loop))
    ax.legend(loc='best')
    ax.text(0.0, 1.01, r"${:.0f}\mathrm{{Hz}}$ $\alpha={:.3f}$".format(transfer.dataset.wfs_rate, transfer.dataset.alpha), transform=ax.transAxes)
    ax.figure.savefig(filename)

def main():
    """Make various generated telemetry components."""
    opt = parser(setup)
    
    session = opt.session
    name = "transferfunction/{0}".format(opt.kind)
    kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == name).one()
    
    query = session.query(Telemetry).join(Telemetry.kind).filter(TelemetryKind.h5path == name)
    if opt.date:
        query = query.join(Dataset).filter(Dataset.id.in_(opt.query))
    
    import seaborn
    import matplotlib.pyplot as plt
    plt.clf()
    ax = plt.gca()
    for transfer in query.all():
        print(transfer)
        print(transfer.dataset)
        ax.clear()
        plot_transfer(transfer, ax)
    session.commit()

if __name__ == '__main__':
    main()

