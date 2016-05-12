# -*- coding: utf-8 -*-

import os

__all__ = ['save_ax_telemetry']

def save_ax_telemetry(telemetry, func, *args, **kwargs):
    """Save a figure created by a function."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    category = kwargs.pop('category')
    
    func(ax, telemetry, *args, **kwargs)
    filename = os.path.join(telemetry.dataset.path, 
        "figures", "{0:s}".format(category), 
        "s{0:04d}.{1:s}.png".format(telemetry.dataset.sequence, 
        telemetry.kind.h5path.replace("/", ".")))
    
    if not os.path.isdir(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    
    fig.savefig(filename)
    return filename
    
