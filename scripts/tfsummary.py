#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Transfer Function Summaries
"""
import sys, argparse, glob, os

def main():
    """Main function for parsing."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=set("sx sy coefficients".split()))
    opt = parser.parse_args()
    import numpy as np
    import astropy.units as u
    import matplotlib
    # matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    
    from telemetry import connect, makedirs
    Session = connect()
    session = Session()
    from telemetry.models import TransferFunction, TransferFunctionModel, Sequence
    from telemetry.views.periodogram import show_periodogram
    
    
    
    tfs = session.query(TransferFunction).filter(TransferFunction.kind == opt.kind).join(Sequence).filter(Sequence.id > 24)
    ntf = tfs.count()
    
    eff_gain = np.zeros((ntf,))
    sig_gain = np.zeros((ntf,))
    tru_gain = np.zeros((ntf,))
    
    for i, tf in enumerate(tfs.all()):
        tfm = tf.sequence.transferfunctionmodels[tf.kind]
        
        filename = os.path.join(tf.sequence.figure_path, "transfer", "s{0:04d}".format(tf.sequence.id))
        makedirs(os.path.dirname(filename))
        
        if not (tfm.gain == 0.0).all():
            
            tru_gain[i] = tf.sequence.gain
            eff_gain[i] = tfm.gain.mean()
            sig_gain[i] = tfm.gain.std()
            
            fig, (ax_1, ax_2, ax_3) = plt.subplots(3,1, sharex=True, figsize=(6, 8))
            fig.suptitle("Parameter as a function of coefficient for s{0:04d} gain={1:.2f}".format(tf.sequence.id, tf.sequence.gain))
            
            # Plot Gain
            ax_1.set_xlim(0, 224)
            ax_1.plot(tfm.gain, 'g.', label='fit')
            ax_1.axhline(tf.sequence.gain, color='r', label='expected')
            ax_1.set_ylabel("Gain")
            ax_1.set_ylim(0.0, np.max([tfm.gain.max(), np.min([tf.sequence.gain + 0.1, 1.0])]))
            
            # Plot Tau
            ax_2.plot(tfm.tau, 'g.', label='fit')
            ax_2.axhline(1.0/tf.sequence.rate, color='r', ls=':', label='expected')
            ax_2.set_ylabel("Tau (s)")
            ax_2.set_ylim(0.0, tfm.tau.max())
            ax_2.legend(loc='best', fontsize='x-small')
            
            # Plot Integrator
            ax_3.plot(tfm.integrator, 'g.', label='fit')
            ax_3.axhline(tf.sequence.tweeter_bleed, color='r', label='expected')
            ax_3.set_ylabel("Bleed")
            ax_3.set_ylim(np.min([tfm.integrator.min(), 0.88]), 1.0)
            
            fig.savefig(filename + ".tffit.{:s}.png".format(opt.kind))
            plt.close(fig)
            
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    ax.errorbar(tru_gain, eff_gain, yerr=sig_gain, fmt='k.', ls='none')
    ax.set_xlabel("Gain Setting")
    ax.set_ylabel("Gain Fit")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 0.2)
    
    plt.savefig(os.path.dirname(filename) + "gain_trend.png")

if __name__ == '__main__':
    main()