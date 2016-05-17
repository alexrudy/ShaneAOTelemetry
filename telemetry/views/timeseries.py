# -*- coding: utf-8 -*-
"""
Plot a time-series object.
"""
import os
import numpy as np
from .core import save_ax_telemetry, construct_filename
from ..application import app
from ..models import Dataset

def timeseries(ax, telemetry, **kwargs):
    """Plot a telemetry timeseries."""
    data = telemetry.read()
    n_modes = np.prod(data.shape[1:])
    time = np.arange(data.shape[-1]) / telemetry.dataset.rate
    
    kwargs.setdefault('color', 'k')
    kwargs.setdefault('alpha', 0.01)
    
    data = data.transpose()
    data = data.reshape((data.shape[0], -1))
    ax.plot(time, data, **kwargs)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("{0:s}".format(telemetry.kind.name))
    ax.set_title("Timeseries of {0:s} from {1:s}".format(
        telemetry.kind.name, telemetry.dataset.title()))
    ax.set_xlim(np.min(time), np.max(time))

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
    
    

class PhaseMovieView(object):
    """A view for a phase movie, the main phase view area, attached to a single axes object."""
    def __init__(self, ax, cube, norm=None, cmap='jet', title='Phase at {0:f}/{1:f}', 
        cb_show=True, cb_label='Phase error (nm)', time=None, **kwargs):
        super(PhaseMovieView, self).__init__()
        from matplotlib.colors import Normalize
        
        self.ax = ax
        self.cube = cube
        
        if norm is None:
            norm = Normalize()
        self.norm = norm
        
        self.cmap = cmap
        self.cb_label = cb_label
        self.cb_show = cb_show
        self.title = title
        
        if time is None:
            time = np.arange(self.cube.shape[0], dtype=np.float)
        self.time = time
        self._index = 0
        self.paused = False
        
        
        self._image_kwargs = kwargs
        self._setup = False
        self._connections = {}
        
    def symlognorm(self, n_sigma=3):
        """Set up the symmetric log normalizer."""
        from matplotlib.colors import SymLogNorm
        nonzero = np.abs(self.cube[self.cube != 0.0])
        limit = np.mean(nonzero) - n_sigma * np.std(nonzero)
        self.norm = SymLogNorm(limit, linscale=0.01)
        
    def setup(self):
        """Setup the axes."""
        self._image = self.ax.imshow(self.cube[0,...],interpolation='nearest', cmap=self.cmap, norm=self.norm, **self._image_kwargs)
        self._title = self.ax.set_title(self.title.format(self.time[self._index], self.time[-1]))
        if self.cb_show:
            self._colorbar = self.ax.figure.colorbar(self._image, ax=self.ax)
            self._colorbar.set_label(self.cb_label)
        self._setup = True
        
    def update(self, i=None):
        """Update this axis."""
        if i is None and not self.paused:
            self._index += 1
        else:
            self._index = i
        
        if not self._setup:
            self.setup()
        
        self._image.set_data(self.cube[self._index,...])
        self._title.set_text(self.title.format(self.time[self._index], self.time[-1]))

class PhaseSummaryPlot(object):
    """A summary plot overlaied with a playbar."""
    def __init__(self, ax, time=None, x_label='', y_label=''):
        super(PhaseSummaryPlot, self).__init__()
        self.ax = ax
        self.x_label = x_label
        self.y_label = y_label
        self.time = time
        self._index = 0
        self.paused = False
        self._connections = {}
        self._setup = False
        
    def setup(self):
        """Set up the plot for plotting."""
        self._playbar = self.ax.axvline(0.0, color='r', linewidth=3, alpha=0.5)
        self.ax.set_ylabel(self.y_label)
        self.ax.set_xlabel(self.x_label)
        self._setup = True
        
    def update(self, i=None):
        """docstring for update"""
        if i is None and not self.paused:
            self._index += 1
        else:
            self._index = i
        
        if not self._setup:
            self.setup()
            
        vline_xdata, vline_ydata = self._playbar.get_data()
        if self.time is None:
            t = self._index
        else:
            t = self.time[self._index]
        vline_xdata[:] = np.array([t, t], dtype=np.float)
        self._playbar.set_data(vline_xdata, vline_ydata)
        
    

@app.celery.task(bind=True)
def make_movie(self, dataset_id, component, cmap='viridis', shape=(32,32,-1), sigclip=True, log=False, limit=None, force=False):
    """Make a movie."""
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams['text.usetex'] = False
    matplotlib.rcParams['savefig.dpi'] = 300
    
    from matplotlib.gridspec import GridSpec
    from matplotlib.colors import Normalize, SymLogNorm
    from matplotlib import animation
    import matplotlib.pyplot as plt
    import tqdm
    
    dataset = self.session.query(Dataset).get(dataset_id)
    telemetry = dataset.telemetry[component]
    
    
    filename = construct_filename(telemetry, component, folder='movies', ext='mp4')
    if os.path.exists(filename) and not force:
        return
    
    data = telemetry.read()
    if limit:
        data = data[...,:limit]
    data.shape = shape
    assert data.ndim == 3, "Shape not compatible: {0!r}".format(data.shape)
    frames = data.shape[-1]
    times = np.arange(frames) / telemetry.dataset.rate
    
    if sigclip:
        sigma = np.std(data)
        mean = np.mean(data)
        vlim = (mean - 3 * sigma, mean + 3 * sigma)        
    else:
        vlim = (np.min(data),np.max(data))
    
    if log:
        norm = SymLogNorm(1.0, linscale=0.01, vmin = vlim[0], vmax = vlim[1])
    else:
        norm = Normalize(vmin = vlim[0], vmax = vlim[1])
    
    
    figure = plt.figure(figsize=(9,9))
    gs = GridSpec(2, 1, height_ratios=[1, 0.25])
    
    rms_ax = figure.add_subplot(gs[1,:])
    rms = PhaseSummaryPlot(rms_ax, time=times, x_label='Time', y_label="RMS nm of phase error")
    rms_ax.plot(times, np.std(data, axis=(0,1)), '-')
    rms_ax.set_xlim(np.min(times), np.max(times))
    
    phase_ax = figure.add_subplot(gs[0,:])
    image = PhaseMovieView(phase_ax, data.T, norm=norm, cmap=cmap, time=times)
    
    fps = 30
    
    
    def animate(n):
        """Animate at index n."""
        image.update(n)
        rms.update(n)

    anim = animation.FuncAnimation(figure, animate, frames=frames, interval=1)
    anim.save(filename, fps=fps, writer='ffmpeg')
    return filename