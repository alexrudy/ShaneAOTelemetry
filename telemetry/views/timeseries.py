# -*- coding: utf-8 -*-
"""
Plot a time-series object.
"""
import numpy as np
from .core import save_ax_telemetry
from ..application import app
from ..models import Dataset

def timeseries(ax, telemetry, **kwargs):
    """Plot a telemetry timeseries."""
    data = telemetry.read()
    n_modes = np.prod(data.shape[1:])
    time = np.arange(data.shape[-1]) / telemetry.dataset.rate
    
    kwargs.setdefault('color', 'k')
    kwargs.setdefault('alpha', 0.01)
    
    ax.plot(time, data.T, **kwargs)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("{0:s}".format(telemetry.kind.name))
    ax.set_title("Timeseries of {0:s} from {1:s}".format(
        telemetry.kind.name, telemetry.dataset.title()))

@app.celery.task(bind=True)
def make_timeseries(self, dataset_id, component):
    """Make a timeseries plot."""
    dataset = self.session.query(Dataset).get(dataset_id)
    telemetry = dataset.telemetry[component]
    return save_ax_telemetry(telemetry, timeseries, category='timeseries')
    
def valueshistogram(ax, telemetry, **kwargs):
    """Values histogram."""
    data = telemetry.read()
    n_modes = np.prod(data.shape[1:])
    time = np.arange(data.shape[-1]) / telemetry.dataset.rate
    
    kwargs.setdefault('color', 'k')
    kwargs.setdefault('bins', 100)
    
    ax.hist(data.flatten(), **kwargs)
    ax.set_ylabel("N")
    ax.set_xlabel("{0:s}".format(telemetry.kind.name))
    ax.set_title("Histogram of {0:s} from {1:s}".format(
        telemetry.kind.name, telemetry.dataset.title()))
        
    
@app.celery.task(bind=True)
def make_histogram(self, dataset_id, component):
    """Make a timeseries plot."""
    dataset = self.session.query(Dataset).get(dataset_id)
    telemetry = dataset.telemetry[component]
    return save_ax_telemetry(telemetry, valueshistogram, category='histogram')
    