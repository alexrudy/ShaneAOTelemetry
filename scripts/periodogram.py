#!/usr/bin/env python
"""
Create telemetry objects from datasets.
"""

import sys, argparse, glob, os, datetime

def main():
    """Main function for parsing."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=set("sx sy hcoefficients fmodes phase pseudophase pseudophasentt".split()))
    opt = parser.parse_args()
    
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams['text.usetex'] = False
    from telemetry import connect, makedirs
    Session = connect()
    from telemetry.models import Dataset, Periodogram, PeriodogramStack, Sequence
    session = Session()
    from telemetry.views.periodogram import show_periodogram
    from astropy.utils.console import ProgressBar
    
    n_telemetry = 0
    
    query = session.query(PeriodogramStack).filter(PeriodogramStack.kind == opt.kind).join(Sequence).filter(Sequence.date == datetime.datetime(2016,03,24,0,0,0))
    for periodogram in ProgressBar(query.all()):
        
        filename = os.path.join(periodogram.sequence.figure_path, "periodogram", "s{0:04d}.periodogram.{1:s}.png".format(periodogram.sequence.id, opt.kind))
        makedirs(os.path.dirname(filename))
        if os.path.exists(filename):
            continue
        try:
            data = periodogram.read()
            if np.all(data[np.isfinite(data)] == 0.0):
                continue
        except KeyError as e:
            continue
        
        import matplotlib.pyplot as plt
        plt.clf()
        ax = plt.gca()
        show_periodogram(ax, data, rate=periodogram.rate)
        
        ax.set_title('{0:s} Periodogram for s{1:04d} "{2:s}"'.format(opt.kind.capitalize(), periodogram.sequence.id, periodogram.sequence.loop))
        plt.savefig(filename)
    print("Created {:d} images.".format(query.count()))

if __name__ == '__main__':
    main()