#!/usr/bin/env python
"""
Create telemetry objects from datasets.
"""

import sys, argparse, glob, os

def main():
    """Main function for parsing."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=set("sx sy coefficients".split()))
    opt = parser.parse_args()
    
    import matplotlib
    # matplotlib.use("Agg")
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Periodogram, PeriodogramStack, Sequence
    session = Session()
    from telemetry.views.periodogram import show_periodogram
    from astropy.utils.console import ProgressBar
    
    n_telemetry = 0
    
    query = session.query(PeriodogramStack).filter(PeriodogramStack.kind == opt.kind)
    for periodogram in ProgressBar(query.all()):
        
        filename, ext = os.path.splitext(periodogram.filename)
        
        data = periodogram.read()
        
        import matplotlib.pyplot as plt
        ax = plt.gca()
        show_periodogram(ax, data, rate=periodogram.rate)
        ax.set_title('{0:s} Periodogram for s{1:04d}'.format(opt.kind, periodogram.sequence.id))
        plt.savefig(filename + ".periodogram.{0:s}.png".format(opt.kind))
    print("Created {:d} images.".format(query.count()))

if __name__ == '__main__':
    main()