#!/usr/bin/env python
"""
Create telemetry objects from datasets.
"""

import sys, argparse, glob, os, datetime

def main():
    """Main function for parsing."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=set("sx sy hcoefficients fmodes phase pseudophase".split()))
    parser.add_argument("--index", type=int, default=None, help="Choose an index.")
    parser.add_argument("--fit", action='store_true', help="Redo the fit.")
    
    opt = parser.parse_args()
    import astropy.units as u
    import matplotlib
    matplotlib.rcParams['text.usetex'] = False
    import numpy as np
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from telemetry import connect, makedirs
    Session = connect()
    from telemetry.models import Dataset, Periodogram, PeriodogramStack, Sequence, TransferFunction
    session = Session()
    from telemetry.views.periodogram import show_periodogram, show_model_parameters
    from telemetry.algorithms.transfer.linfit import expected_model, fit_model
    from astropy.utils.console import ProgressBar
    
    n_telemetry = 0
    fig = plt.figure()
    
    query = session.query(TransferFunction).filter(TransferFunction.kind == opt.kind).join(Sequence).filter(Sequence.id > 24)
    query = query.filter(Sequence.date == datetime.datetime(2016,03,24,0,0,0))
    for tf in ProgressBar(query.all()):
        
        filename = os.path.join(tf.sequence.figure_path, "transfer", "s{0:04d}".format(tf.sequence.id))
        makedirs(os.path.dirname(filename))
        
        freq = tf.frequencies.to(u.Hz).value
        tf_data = tf.data
        tf_model = np.exp(expected_model(tf)(freq))
        
        tf_fit = tf.sequence.transferfunctionmodels[tf.kind]
        tf_fit_data = np.exp(tf_fit.to_model()(freq[:,None]))
        
        
        fig.clear()
        ax = fig.add_subplot(1,1,1)
        ax.grid(True)
        show_periodogram(ax, tf_model, rate=tf.rate, alpha=1.0, color='r', zorder=0.1, label='model')
        
        if opt.index is not None:
            
            if opt.fit:
                tf_model = fit_model(tf, index=opt.index)
                tf_model_data = np.exp(tf_model(freq))
            else:
                tf_model = tf_fit.to_model(opt.index)
                tf_model_data = tf_fit_data[:,opt.index]
            
            ax.set_title('Transfer Function for s{:04d} gain={:0.2f} mode={:d}'.format(tf.sequence.id, tf.sequence.gain, opt.index))
            show_periodogram(ax, tf_data[:,opt.index], rate=tf.rate, alpha=1.0, label='data')
            show_periodogram(ax, tf_model_data, rate=tf.rate, alpha=1.0, color='g', label='fit')
            show_model_parameters(ax, tf_model, name='Fit')
            show_model_parameters(ax, expected_model(tf), name='Model', pos=(0.8, 0.1))
            
            ax.set_ylim(1e-2, 10)
            ax.legend(fontsize='small', loc='upper center')
            fig.savefig(filename + ".transfer.{:s}.{:03d}.png".format(opt.kind, opt.index))
        else:
            filename = filename + ".transfer.{:s}.png".format(opt.kind)
            if os.path.exists(filename):
                continue
                
            ax.set_title('Transfer Function for s{:04d} gain={:0.2f}'.format(tf.sequence.id, tf.sequence.gain))
            show_periodogram(ax, tf_data, rate=tf.rate, alpha=0.1)
            show_model_parameters(ax, expected_model(tf), name='Model', pos=(0.8, 0.1))
            
            if opt.fit:
                tf_model = fit_model(tf, index=opt.index)
                tf_model_data = np.exp(tf_model(freq))
                show_periodogram(ax, tf_model_data, rate=tf.rate, alpha=1.0, color='g', label='fit')
                show_model_parameters(ax, tf_model, name='Fit')
            
            
            fig.savefig(filename)
    print(filename)
    print("Created {:d} images.".format(query.count()))

if __name__ == '__main__':
    main()