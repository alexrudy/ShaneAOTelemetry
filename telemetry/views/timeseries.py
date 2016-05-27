# -*- coding: utf-8 -*-
"""
Plot a time-series object.
"""
import os
import numpy as np
from .core import telemetry_plotting_task
from ..models import Dataset
from ..application import app
from astropy.convolution import Gaussian1DKernel, convolve

def prepare_timeseries_data(telemetry, flatten=True, real=True):
    """Prepare data for a timeseries, collapsing, etc."""
    data = telemetry.read()
    
    data = data.transpose()
    if flatten and data.size:
        try:
            flat_shape = (data.shape[0], -1)
            data = data.reshape(flat_shape)
        except ValueError as e:
            raise ValueError("<array shape={0!r}>.reshape({1!r}) error: {2!s}".format(
                data.shape, flat_shape, e
            ))
    
    if real and np.iscomplexobj(data):
        data = np.abs(data)
    
    time = np.arange(data.shape[0]) / telemetry.dataset.rate
    return time, data

@telemetry_plotting_task(category='timeseries')
def timeseries(ax, telemetry, select=None, **kwargs):
    """Plot a telemetry timeseries."""
    time, data = prepare_timeseries_data(telemetry)
    
    kwargs.setdefault('color', 'k')
    kwargs.setdefault('alpha', 0.01)
    
    if select is not None:
        data = data[:,select]
    
    lines = ax.plot(time, data, **kwargs)
    
    if select is not None:
        sdata = np.apply_along_axis(lambda a: convolve(a, Gaussian1DKernel(stddev=50), boundary='extend'), 0, data)
        kwargs['alpha'] = 1.0
        for i, line in enumerate(lines):
            kwargs['color'] = line.get_color()
            ax.plot(time, sdata[:,i], **kwargs)
        
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("{0:s}".format(telemetry.kind.name))
    ax.set_title("Timeseries of {0:s} from {1:s}".format(
        telemetry.kind.name, telemetry.dataset.title()))
    ax.set_xlim(np.min(time), np.max(time))
    
@telemetry_plotting_task(category='mean')
def mean(ax, telemetry, **kwargs):
    """Make an average view."""
    time, data = prepare_timeseries_data(telemetry, flatten=False)
    data = data.mean(axis=0)
    if data.ndim == 2:
        mean_2d_view(ax, data, telemetry, **kwargs)
    else:
        data = data.flatten()
        mean_1d_view(ax, data, telemetry, **kwargs)


def mean_2d_view(ax, data, telemetry, **kwargs):
    """2D view of mean data throughout a timeseries."""
    kwargs.setdefault('cmap', 'viridis')
    image = ax.imshow(data, **kwargs)
    ax.figure.colorbar(image, ax=ax)
    ax.grid(False)
    ax.set_title("Mean of {0:s} from {1:s}".format(
        telemetry.kind.name, telemetry.dataset.title()))

def mean_1d_view(ax, data, telemetry, **kwargs):
    """1D view of mean data throughout a timeseries."""
    mode_n = np.arange(data.shape[0])
    image = ax.bar(mode_n, data, **kwargs)
    ax.set_title("Mean of {0:s} from {1:s}".format(
        telemetry.kind.name, telemetry.dataset.title()))
    ax.set_xlim(0, data.shape[0] + 1)

@telemetry_plotting_task(category='histogram')
def histogram(ax, telemetry, **kwargs):
    """Values histogram."""
    time, data = prepare_timeseries_data(telemetry)
    
    kwargs.setdefault('color', 'k')
    kwargs.setdefault('bins', 100)
    
    filterzero = kwargs.pop('filterzero', "fouriercoeffs" in telemetry.kind.h5path)
    data = data.flatten()
    if filterzero:
        data = data[data != 0.0]
    
    ax.hist(data, **kwargs)
    ax.set_ylabel("N")
    ax.set_xlabel("{0:s}".format(telemetry.kind.name))
    ax.set_title("Histogram of {0:s} from {1:s}".format(
        telemetry.kind.name, telemetry.dataset.title()))
        

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