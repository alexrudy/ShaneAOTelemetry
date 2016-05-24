# -*- coding: utf-8 -*-
"""
An analysis of the gain multiplier effect.

These are the generic functions used by specific scripts.
"""

import sys, argparse, glob, os
import datetime
import itertools
import astropy.units as u
import numpy as np

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

def _make_row(tf, tfm, boost_factor=1.0):
    """Make a table row."""
    tf.dataset.instrument_data.control_matrix
    row = tf.dataset.instrument_data.attributes()
    row['CM'] = row.pop('control_matrix')
    row['date'] = tf.dataset.date
    row['gain'] = tf.dataset.gain
    row['rate'] = tf.dataset.rate
    row['bleed'] = tf.dataset.bleed
    row['effective gain'] = tf.dataset.gain * boost_factor
    row['boost'] = boost_factor
    row['fit gain'] = tfm.gain.value.mean()
    row['fit sigma'] = tfm.gain.value.std()
    row['id'] = tf.dataset.id
    row['kind'] = tf.kind.h5path
    return row
    
def plot_results(data, output_directory, filename_root, title):
    """Given a data table of results, plot it!"""
    import matplotlib.pyplot as plt
    
    boosts = set(data["boost"])
    original = data[data["boost"] == 1.0]
    boosted = data[data["boost"] != 1.0]
    boosts = set(boosted["boost"])
    
    
    plt.figure()
    fit_and_plot_gains(data, "Combined", 0.85, "r", show_data=False)
    for boost_factor in boosts:
        fit_and_plot_gains(boosted[boosted['boost'] == boost_factor], r"${:.0f}\times$Boosted".format(boost_factor), 0.9, "g")
    fit_and_plot_gains(original, "Original", 0.95, "b")
    x = np.linspace(0.0, 2.0, 50)
    plt.title(title)
    plt.plot(x, x, alpha=0.1, color='k', ls=":")
    plt.xlabel("Expected Gain Setting")
    plt.ylabel("Gain from Model Fit")
    plt.xlim(0.0, 2.05)
    plt.ylim(0.0, 0.8)
    plt.legend(loc='upper left', fontsize='small')
    filename_trend = os.path.join(output_directory,"{:s}.trend.png".format(filename_root))
    plt.savefig(filename_trend)
    
    plt.figure(figsize=(6,5))
    for boost_factor in boosts:
        fit_and_plot_gains(boosted[boosted['boost'] == boost_factor], r"${:.0f}\times$Boosted".format(boost_factor), 0.95, "g", effective=False, boost=boost_factor)
    plt.ylim(0.0, 1.0)
    plt.xlim(0.0, 1.0)
    plt.xlabel("Expected Gain Setting")
    plt.ylabel("Gain from Model Fit")
    plt.title(title)
    plt.legend(loc='upper left', fontsize='small')
    x = np.linspace(0.0, 2.0, 50)
    plt.plot(x, x, alpha=0.1, color='k', ls=":")
    plt.gca().set_aspect('equal')
    filename_boost = os.path.join(output_directory,"{:s}.boost.png".format(filename_root))
    plt.savefig(filename_boost)
    
def gather_query(query, boost_factor, elimintate):
    """For a query on TransferFunction, gather relevant rows."""
    for telemetry in query.all():
        model = telemetry.read()
        if not (model.gain == 0.0).all():
            yield _make_row(telemetry, model, boost_factor=boost_factor)
    

def generate_table(query_base, eliminate):
    """Generate a table from a query base."""
    from astropy.table import Table
    from telemetry.models import Sequence, TransferFunction
    query_default = query_base.filter(Sequence.control_matrix == "Default")
    query_boosted = query_base.filter(Sequence.control_matrix == "Rudy")
    data = Table(list(itertools.chain(gather_query(query_default, 1.0, eliminate), gather_query(query_boosted, 4.0, eliminate))))
    return data
    
def analyze_table(data, output_directory):
    """Analyze a table."""
    ao_rates = set(data['rate'])
    boosts = set(data['boost'])
    for rate in ao_rates:
        filename_root = "gain-trends-{:.0f}Hz".format(rate)
        title = "ShaneAO at {:.0f}Hz".format(rate)
        plot_results(data[data['rate'] == rate], output_directory, filename_root, title)
