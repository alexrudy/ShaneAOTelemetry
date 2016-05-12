# -*- coding: utf-8 -*-

import os

__all__ = ['save_ax_telemetry', 'construct_filename']

def construct_filename(telemetry, category, folder='figures', ext='png'):
    """Construct a filename."""
    filename = os.path.join(telemetry.dataset.path, 
        folder, category, 
        "s{0:04d}.{1:s}.{2:s}".format(telemetry.dataset.sequence, 
        telemetry.kind.h5path.replace("/", "."), ext))
    
    if not os.path.isdir(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    return filename

def save_ax_telemetry(telemetry, func, *args, **kwargs):
    """Save a figure created by a function."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    category = kwargs.pop('category')
    
    func(ax, telemetry, *args, **kwargs)
    filename = construct_filename(telemetry, category)
    fig.savefig(filename)
    return filename
    
