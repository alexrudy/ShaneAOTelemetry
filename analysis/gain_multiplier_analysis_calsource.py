#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An analysis of the gain multiplier effect.
"""

import sys, argparse, glob, os
import datetime
import astropy.units as u
import numpy as np
import matplotlib
matplotlib.use("Agg")

def fit_and_plot_gains(gains, label, label_ypos, color, show_data=True):
    """Fit and plot a bunch of gains."""
    import matplotlib.pyplot as plt
    
    data = np.array(gains)
    expected_gain = data[:,0]
    model_gain = data[:,1]
    model_noise = data[:,2]
    
    y = model_gain * np.sqrt(1.0/model_noise)
    A = np.vstack([expected_gain, np.ones(len(expected_gain))]).T
    A *= np.sqrt(1.0/model_noise)[:,None]
    m, c = np.linalg.lstsq(A, y)[0]
    
    if show_data:
        plt.errorbar(expected_gain, model_gain, yerr=model_noise, fmt='.', ls='none', label=label, color=color)
    
    x = np.linspace(0.0, 2.0, 50)
    plt.plot(x, x * m + c, '-', label="{} Fit: $m={:.2f}$ $c={:.2f}$".format(label, m, c), color=color, alpha=0.3)
    # plt.text(0.01, label_ypos, r"{} Fit: $m={:.2f}$ $c={:.2f}$".format(label, m, c), transform=plt.gca().transAxes)

def main():
    """Main function for parsing."""
    parser = argparse.ArgumentParser()
    opt = parser.parse_args()
    
    # Handle imports
    import matplotlib.pyplot as plt
    
    from telemetry import connect
    from telemetry.models import Dataset, Periodogram, PeriodogramStack, Sequence, TransferFunction
    Session = connect()
    session = Session()
    
    query_tf = session.query(TransferFunction).filter(TransferFunction.kind == "coefficients").join(Sequence)
    query = query_tf.filter(Sequence.date == datetime.datetime(2016, 01, 22))
    
    gain = set()
    
    for tf in query.all():
        tfm = tf.sequence.transferfunctionmodels[tf.kind]
        if not (tfm.gain == 0.0).all() and len(tf.sequence.datasets) > 5:
            gain.add((tf.sequence.gain, tfm.gain.mean(), tfm.gain.std()))
    gain = list(gain)
    
    boosted_gain = []
    query = query_tf.filter(Sequence.date == datetime.datetime(2016, 03, 16))
    for tf in query.all():
        tfm = tf.sequence.transferfunctionmodels[tf.kind]
        if not (tfm.gain == 0.0).all():
            boosted_gain.append((tf.sequence.gain * 4.0, tfm.gain.mean(), tfm.gain.std())) 
    
    
    fit_and_plot_gains(gain + boosted_gain, "Combined", 0.85, "r", show_data=False)
    fit_and_plot_gains(boosted_gain, r"$4\times$Boosted", 0.9, "g")
    fit_and_plot_gains(gain, "Original", 0.95, "b")
    x = np.linspace(0.0, 2.0, 50)
    plt.plot(x, x, alpha=0.1, color='k', ls=":")
    plt.xlabel("Expected Gain Setting")
    plt.ylabel("Gain from Model Fit")
    plt.xlim(0.0, 2.0)
    plt.ylim(0.0, 0.8)
    plt.legend(loc='upper left', fontsize='small')
    plt.savefig("gain-trend.png")
    
    plt.figure(figsize=(6,5))
    data = np.array(boosted_gain)
    data[:,0] /= 4.0
    fit_and_plot_gains(data, r"$4\times$Boosted", 0.95, "g")
    plt.ylim(0.0, 1.0)
    plt.xlim(0.0, 1.0)
    plt.legend(loc='lower right', fontsize='small')
    x = np.linspace(0.0, 2.0, 50)
    plt.plot(x, x, alpha=0.1, color='k', ls=":")
    plt.gca().set_aspect('equal')
    plt.savefig("gain-new.png")

if __name__ == '__main__':
    main()