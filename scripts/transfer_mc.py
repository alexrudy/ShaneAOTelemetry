#!/usr/bin/env python
"""
Fit and plot telemetry with MCMC
"""

import sys, argparse, glob, os

def main():
    """Main function for parsing."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=set("sx sy coefficients fmodes".split()))
    parser.add_argument("--index", type=int, default=None, help="Choose an index.")
    parser.add_argument("--fit", action='store_true', help="Redo the fit.")
    
    opt = parser.parse_args()
    import astropy.units as u
    import matplotlib
    import numpy as np
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from telemetry import connect, makedirs
    Session = connect()
    from telemetry.models import Dataset, Periodogram, PeriodogramStack, Sequence, TransferFunction
    session = Session()
    from telemetry.views.periodogram import show_periodogram, show_model_parameters
    from telemetry.algorithms.transfer.mcmc import fit_emcee, plot_emcee
    from astropy.utils.console import ProgressBar
    
    n_telemetry = 0
    
    query = session.query(TransferFunction).filter(TransferFunction.kind == opt.kind).join(Sequence).filter(Sequence.id > 24)
    for tf in ProgressBar(query.all()):
        
        filename = os.path.join(tf.sequence.figure_path, "transfer", "s{0:04d}".format(tf.sequence.id))
        makedirs(os.path.dirname(filename))
        
        freq = tf.frequencies.to(u.Hz).value
        
        if opt.index is not None:
            
            samples = fit_emcee(tf, index=opt.index)
            plot_emcee(samples, tf)
            plt.savefig(filename + ".transfer.mcmc.{:s}.png".format(opt.kind))

if __name__ == '__main__':
    main()