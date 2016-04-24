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
    parser.add_argument("kind", type=str, help="Data kind to periodogram.")

def plot_periodogram(periodogram, ax):
    """Plot a periodogram."""
    filename = os.path.join(periodogram.dataset.path,"figures", "periodogram", "s{0:04d}.periodogram.{1:s}.png".format(periodogram.dataset.sequence, periodogram.kind.kind))
    makedirs(os.path.dirname(filename))
    data = periodogram.read()
    show_periodogram(ax, data.T, rate=periodogram.dataset.wfs_rate)
    ax.set_title('{0:s} Periodogram for s{1:04d} "{2:s}"'.format(periodogram.kind.kind.capitalize(), periodogram.dataset.sequence, periodogram.dataset.loop))
    ax.figure.savefig(filename)

def main():
    """Make various generated telemetry components."""
    opt = parser(setup)
    
    session = opt.session
    name = "{0} periodogram".format(opt.kind)
    print(name)
    kind = session.query(TelemetryKind).filter(TelemetryKind.name == name).one()
    query = session.query(Telemetry).join(Telemetry.kind).filter(TelemetryKind.name == name)#.filter(Dataset.id.in_(opt.query))
    
    import seaborn
    import matplotlib.pyplot as plt
    plt.clf()
    ax = plt.gca()
    for periodogram in query.all():
        print(periodogram)
        print(periodogram.dataset)
        ax.clear()
        plot_periodogram(periodogram, ax)
    session.commit()

if __name__ == '__main__':
    main()

