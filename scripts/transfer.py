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
    parser.add_argument("--index", type=int, default=None, help="Choose an index.")
    opt = parser.parse_args()
    import astropy.units as u
    import matplotlib
    # matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Periodogram, PeriodogramStack, Sequence, TransferFunction
    session = Session()
    from telemetry.views.periodogram import show_periodogram, show_model_parameters
    from telemetry.algorithms.transfer.model import expected_model, fit_model
    from astropy.utils.console import ProgressBar
    
    n_telemetry = 0
    fig = plt.figure()
    
    query = session.query(TransferFunction).filter(TransferFunction.kind == opt.kind).join(Sequence).filter(Sequence.id > 24)
    for tf in ProgressBar(query.all()):
        
        filename, ext = os.path.splitext(tf.filename)
        
        tf_data = tf.data
        tf_model = expected_model(tf, tau=0.005)(tf.frequencies.to(u.Hz).value)
        fig.clear()
        ax = fig.add_subplot(1,1,1)
        ax.set_title('Transfer Function for s{:04d} gain={:0.2f}'.format(tf.sequence.id, tf.sequence.gain))
        ax.grid(True)
        show_periodogram(ax, tf_model, rate=tf.rate, alpha=1.0, color='r', zorder=0.1, label='model')
        
        if opt.index is not None:
            tf_model = fit_model(tf, tau=0.005, index=opt.index)
            print(expected_model(tf, tau=0.005))
            print(tf_model)
            show_periodogram(ax, tf_data[:,opt.index], rate=tf.rate, alpha=1.0, label='data')
            show_periodogram(ax, tf_model(tf.frequencies.to(u.Hz).value), rate=tf.rate, alpha=1.0, color='g', label='fit')
            show_model_parameters(ax, tf_model)
            ax.legend()
            fig.savefig(filename + ".transfer.{:s}.{:03d}.png".format(opt.kind, opt.index))
        else:
            show_periodogram(ax, tf_data, rate=tf.rate, alpha=0.1)
            fig.savefig(filename + ".transfer.{:s}.png".format(opt.kind))
    print(filename)
    print("Created {:d} images.".format(query.count()))

if __name__ == '__main__':
    main()