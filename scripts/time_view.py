#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
import os
from telemetry.cli import parser
from telemetry import makedirs
from telemetry.models import Telemetry, TelemetryKind, Dataset, Periodogram

from telemetry.views.periodogram import show_periodogram
from astropy.utils.console import ProgressBar

import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams['text.usetex'] = False

def setup(parser):
    """Set up the argument parser"""
    parser.add_argument("kind", type=str, help="Data kind to plot.")

def plot_telemetry(telemetry, ax):
    """Plot telemetry timeseries."""
    filename = os.path.join(telemetry.dataset.path,"figures", "s{0:04d}.{1:s}.png".format(telemetry.dataset.sequence, telemetry.kind.kind))
    makedirs(os.path.dirname(filename))
    data = telemetry.read()[1:,:]
    if not np.isfinite(data).all():
        raise ValueError("Non-finite data: {0}".format(data))
    print(data)
    t = np.arange(data.shape[1]) / telemetry.dataset.wfs_rate
    if not np.isfinite(t).all():
        raise ValueError("Non-finite time: {0}".format(t))
    ax.plot(t, data.T, 'k.', alpha=0.1)
    ax.set_title('{0:s} for s{1:04d} "{2:s}"'.format(telemetry.kind.kind.capitalize(), telemetry.dataset.sequence, telemetry.dataset.loop))
    ax.figure.savefig(filename)

def main():
    """Make various generated telemetry components."""
    opt = parser(setup)
    
    session = opt.session
    kind = session.query(TelemetryKind).filter(TelemetryKind.name == opt.kind).one()
    query = session.query(Telemetry).join(Telemetry.kind).filter(TelemetryKind.name == opt.kind)#.filter(Dataset.id.in_(opt.query))
    
    import seaborn
    import matplotlib.pyplot as plt
    plt.clf()
    ax = plt.gca()
    for telemetry in query.all():
        print(telemetry)
        ax.clear()
        plot_telemetry(telemetry, ax)
    session.commit()

if __name__ == '__main__':
    main()

