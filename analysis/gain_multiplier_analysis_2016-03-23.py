#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An analysis of the gain multiplier effect.
"""

import sys, argparse, glob, os
import datetime
import astropy.units as u
from astropy.table import Table, vstack
import numpy as np
import matplotlib
matplotlib.use("Agg")

def fit_and_plot_gains(gains, label, label_ypos, color, show_data=True, effective=True, boost=None):
    """Fit and plot a bunch of gains."""
    import matplotlib.pyplot as plt
    
    if effective:
        expected_gain = np.asarray(gains['effective gain'])
    else:
        expected_gain = np.asarray(gains['gain'])
    model_gain = np.asarray(gains['fit gain'])
    model_noise = np.asarray(gains['fit sigma'])
    
    y = model_gain * np.sqrt(1.0/model_noise)
    A = np.vstack([expected_gain, np.zeros(len(expected_gain))]).T
    A *= np.sqrt(1.0/model_noise)[:,None]
    m, c = np.linalg.lstsq(A, y)[0]
    
    if show_data:
        plt.errorbar(expected_gain, model_gain, yerr=model_noise, fmt='.', ls='none', label=label, color=color)
    
    x = np.linspace(0.0, 2.0, 50)
    plt.plot(x, x * m + c, '-', label="{} Fit: $m={:.2f}$ $c={:.2f}$".format(label, m, c), color=color, alpha=0.3)
    
    if boost is not None:
        eboost = float(boost) / float(m)
        plt.text(0.98, 0.98, "fit boost: {:.1f}".format(eboost), transform=plt.gca().transAxes, ha='right', va='top')
    return m, c

GAIN_MULTIPLIER = 4.0
ELIMINTATE = [396, 405, 366]
OUTPUT_DIRECTORY = os.path.join("gain_trends","2016-03-23")

def _make_row(tf, tfm, boosted=False):
    """Make a table row."""
    row = tf.sequence.get_sequence_attributes()
    row['CM'] = row.pop('control_matrix')
    row['date'] = row['date'].date()
    row['gain'] = tf.sequence.gain
    row['effective gain'] = tf.sequence.gain * (GAIN_MULTIPLIER if boosted else 1.0)
    row['fit gain'] = tfm.gain.mean()
    row['fit sigma'] = tfm.gain.std()
    row['seq'] = "{:d}-{:d}".format(min(tf.sequence.sequence_numbers()), max(tf.sequence.sequence_numbers()))
    row['id'] = tf.sequence.id
    return row

def main():
    """Main function for parsing."""
    parser = argparse.ArgumentParser()
    opt = parser.parse_args()
    
    # Handle imports
    import matplotlib
    matplotlib.rcParams['text.usetex'] = False
    import matplotlib.pyplot as plt
    from telemetry import connect
    from telemetry.models import Dataset, Periodogram, PeriodogramStack, Sequence, TransferFunction
    Session = connect()
    session = Session()
    tables = []
    for rate in [250, 500, 1000]:
        query_tf = session.query(TransferFunction).filter(TransferFunction.kind == "hcoefficients").join(Sequence)
        query_tf = query_tf.filter(Sequence.date == datetime.datetime(2016, 03, 24, 0, 0, 0)).filter(Sequence.rate == rate)
        query = query_tf.filter(Sequence.control_matrix == "Default")
        rows = []
        for tf in query.all():
            tfm = tf.sequence.transferfunctionmodels[tf.kind]
            eliminate = any([ seq in ELIMINTATE for seq in tf.sequence.sequence_numbers() ])
            if not (tfm.gain == 0.0).all() and len(tf.sequence.datasets) >= 3 and not eliminate:
                rows.append(_make_row(tf, tfm, boosted=False))
        gain = Table(rows)
        gain.pprint()
        rows = []
        query = query_tf.filter(Sequence.control_matrix == "Rudy")
        for tf in query.all():
            tfm = tf.sequence.transferfunctionmodels[tf.kind]
            eliminate = any([ seq in ELIMINTATE for seq in tf.sequence.sequence_numbers() ])
            if not (tfm.gain == 0.0).all() and len(tf.sequence.datasets) >= 3 and not eliminate:
                rows.append(_make_row(tf, tfm, boosted=True))
        boosted_gain = Table(rows)
        boosted_gain.pprint()
        
        joint = vstack((gain, boosted_gain))
        tables.append(joint)
        plt.figure()
        fit_and_plot_gains(joint, "Combined", 0.85, "r", show_data=False)
        fit_and_plot_gains(boosted_gain, r"${:.0f}\times$Boosted".format(GAIN_MULTIPLIER), 0.9, "g")
        fit_and_plot_gains(gain, "Original", 0.95, "b")
        x = np.linspace(0.0, 2.0, 50)
        plt.title("ShaneAO at {:.0f}Hz".format(rate))
        plt.plot(x, x, alpha=0.1, color='k', ls=":")
        plt.xlabel("Expected Gain Setting")
        plt.ylabel("Gain from Model Fit")
        plt.xlim(0.0, 2.0)
        plt.ylim(0.0, 0.8)
        plt.legend(loc='upper left', fontsize='small')
        plt.savefig(os.path.join(OUTPUT_DIRECTORY,"gain-trend-{:d}.png".format(rate)))
        
        plt.figure(figsize=(6,5))
        fit_and_plot_gains(boosted_gain, r"${:.0f}\times$Boosted".format(GAIN_MULTIPLIER), 0.95, "g", effective=False, boost=4.0)
        plt.ylim(0.0, 1.0)
        plt.xlim(0.0, 1.0)
        plt.xlabel("Expected Gain Setting")
        plt.ylabel("Gain from Model Fit")
        plt.title("ShaneAO at {:.0f}Hz".format(rate))
        plt.legend(loc='upper left', fontsize='small')
        x = np.linspace(0.0, 2.0, 50)
        plt.plot(x, x, alpha=0.1, color='k', ls=":")
        plt.gca().set_aspect('equal')
        plt.savefig(os.path.join(OUTPUT_DIRECTORY,"gain-new-{:d}.png".format(rate)))
    
    master = vstack(tables)
    master['fit gain'].format = "{:.3f}"
    master['fit sigma'].format = "{:.3f}"
    master.write(os.path.join(OUTPUT_DIRECTORY,"gain_trends.txt"), format='ascii.fixed_width')
    
if __name__ == '__main__':
    main()