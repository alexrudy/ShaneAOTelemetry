# -*- coding: utf-8 -*-

import os
import functools
from ..application import app
from ..models import Dataset, TelemetryKind


__all__ = ['save_ax_telemetry', 'construct_filename', 'telemetry_plotting_task']

def construct_filename(telemetry, category, folder='figures', ext='png'):
    """Construct a filename."""
    filename = os.path.join(telemetry.dataset.path, 
        folder, "s{0:04d}".format(telemetry.dataset.sequence), telemetry.kind.h5path.replace("/", "."), 
        "{0:s}.s{1:04d}.{2:s}.{3:s}".format(category, telemetry.dataset.sequence, 
        telemetry.kind.h5path.replace("/", "."), ext))
    
    if not os.path.isdir(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    return filename

def save_ax_telemetry(telemetry, func, *args, **kwargs):
    """Save a figure created by a function."""
    category = kwargs.pop('category')
    force = kwargs.pop('force', False)
    filename = construct_filename(telemetry, category)
    
    if (os.path.exists(filename) and not force):
        return filename
    
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure()
    if matplotlib.rcParams['text.usetex']:
        fpath = r"\verb+{0}+".format(telemetry.dataset.filename)
    else:
        fpath = telemetry.dataset.filename
    fig.text(0,0, "{0}:{1}".format(telemetry.dataset.id,fpath), fontsize='small')
    ax = fig.add_subplot(1,1,1)
    
    func(ax, telemetry, *args, **kwargs)
    fig.savefig(filename)
    return filename
    
def telemetry_plotting_task(**default_kwargs):
    """Make a task for plotting telemetry.."""
    
    @functools.wraps(telemetry_plotting_task)
    def decorator(f):
        @app.celery.task(bind=True)
        @functools.wraps(f)
        def _plot_task(self, dataset_id, component_id, **kwargs):
            import matplotlib
            matplotlib.use("Agg")
            import seaborn
            dataset = self.session.query(Dataset).get(dataset_id)
            component = self.session.query(TelemetryKind).get(component_id)
            telemetry = dataset.telemetry[component.h5path]
            for key, value in default_kwargs.items():
                kwargs.setdefault(key, value)
            return save_ax_telemetry(telemetry, f, **kwargs)
        
        return _plot_task
    return decorator
