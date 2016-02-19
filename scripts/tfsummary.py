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
    
    import astropy.units as u
    import matplotlib
    # matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    
    from telemetry import connect
    Session = connect()
    session = Session()
    from telemetry.models import TransferFunction, TransferFunctionModel, Sequence
    from telemetry.views.periodogram import show_periodogram
    

    
    tfs = session.query(TransferFunction).filter(TransferFunction.kind == opt.kind).join(Sequence).filter(Sequence.id > 24)
    for tf in tfs.all():
        tfm = tf.sequence.transferfunctionmodels[tf.kind]
        filename, ext = os.path.splitext(tf.filename)
        
        if not (tfm.gain == 0.0).all():
            fig, (ax_1, ax_2, ax_3) = plt.subplots(3,1, sharex=True)
            fig.suptitle("Parameter as a function of coefficient for s{0:04d} gain={1:.2f}".format(tf.sequence.id, tf.sequence.gain))
            
            ax_1.set_xlim(0, 1024)
            ax_1.plot(tfm.gain, 'b.')
            ax_1.axhline(tf.sequence.gain, color='r')
            ax_1.set_ylabel("Gain")
            ax_2.plot(tfm.tau, 'b.')
            ax_2.set_ylabel("Tau")
            ax_3.plot(tfm.integrator, 'b.')
            ax_3.axhline(tf.sequence.tweeter_bleed, color='r')
            ax_3.set_ylabel("Bleed")
            fig.savefig(filename + ".tffit.{:s}.png".format(opt.kind))

if __name__ == '__main__':
    main()