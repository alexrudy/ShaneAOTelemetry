# -*- coding: utf-8 -*-
"""
Utilities for telemetry quick-look.
"""

import click
import os
from os.path import join as pjoin
import functools
import inspect

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as mgrid
import matplotlib.colors as mnorm

import numpy as np
import h5py
import astropy.units as u
import datetime as dt

from astropy.visualization import quantity_support

import contextlib
import collections

from ShadyAO.config import ShadyConfigParser
from ShadyAO.tweeter import tweeter_aperture

from telemetry.ext.fourieranalysis.modeling.model import TransferFunction
from telemetry.ext.fourieranalysis.modeling.linfit import apply_LevMarLSQFitter

def configure():
    """Generate a configuration"""
    global cfg, ap, library
    root = os.path.expanduser(os.path.join("~/Development/ShaneAO/ShWLSimulator","ShadyAO.cfg"))
    cfg = ShadyConfigParser(root)
    cfg.load_mode('16x')
    click.echo("Configuring ShadyAO in mode {0} from ShadyAO.cfg".format(cfg.get("reconstructor","mode")))
    ap = tweeter_aperture(cfg)
    
    # Show some information about this configuration.
    click.echo("Number of subapertures: {:d}".format(cfg.getint('WFS','ns')))
    click.echo("Size of full grid of phase data points: {0:d}x{0:d}".format(cfg.getint('reconstructor','ng')))
    click.echo("Number of tweeter actuators: {:d}".format(cfg.getint('tweeter','na')))
    
    # Load the ShadyAO matrix library.
    from ShadyAO.controlmatrix import MatrixLibrary
    library = MatrixLibrary(cfg)

def generate_fmodes(t):
    """Generate fmdoes for telemetry"""
    time, phase = t['pseudophase']
    fmodes = np.fft.fftshift(np.fft.fftn(phase * ap[...,None], axes=(0,1)), axes=(0,1))
    t['fmodes'] = time, fmodes
    
class Slicer(object):
    """A slicer, returns proper slice syntax."""
    
    def __getitem__(self, key):
        """Convert to slice objects"""
        return key

slicer = Slicer()

class TelemetryContainer(collections.MutableMapping):
    """A telemetry container"""
    def __init__(self, group, n, date):
        super(TelemetryContainer, self).__init__()
        self.group = group
        self.n = n
        self.date = date
        self._cache = {}
        
    def __iter__(self):
        return iter(self._cache)
    
    def __len__(self):
        return len(self._cache)
        
    def __getitem__(self, key):
        """Return a data key."""
        try:
            return self._cache[key]
        except KeyError:
            v = self._cache[key] = read(self.group[key])
            return v
        
    def __setitem__(self, key, value):
        """Set an item."""
        self._cache[key] = value
        
    def __delitem__(self, key):
        """Delete item."""
        del self._cache[key]
        
    def generate(self, key, func):
        """Generate a telemetry form."""
        self._cache[key] = func(self)

rate_enumeration = {
    1: 50.0 * u.Hz,
    2: 100.0 * u.Hz,
    3: 250.0 * u.Hz,
    4: 500.0 * u.Hz,
    5: 700.0 * u.Hz,
    6: 1000.0 * u.Hz,
    7: 1300.0 * u.Hz,
    8: 1500.0 * u.Hz,
}
def parse_rate(value):
    """docstring for parse_rate"""
    if isinstance(value, int) and (0 <= value <= 7): 
        # Rate was set as an enumeration?
        rate = rate_enumeration.get(value, value * u.Hz)
    else:
        rate = u.Quantity(float(value), u.Hz)
    return rate

def read(h5group):
    """Read a masked group"""
    mask = h5group['mask'][...] == 1
    assert mask.any(), "Some elements must be valid."
    axis = int(h5group['data'].attrs.get("TAXIS", 0))
    rate = parse_rate(h5group.attrs.get("WFSCAMRATE", 1.0))
    n = h5group['data'].shape[axis]
    times = np.linspace(0, n / rate.value, n) / rate.unit
    mtimes = np.compress(mask, times)
    mdata = np.compress(mask, h5group['data'], axis=axis)
    mdata = np.moveaxis(mdata, axis, -1)
    if h5group.name.endswith('tweeter') or h5group.name.endswith("coefficients"):
        mdata = mdata.reshape((32, 32, -1))
    return mtimes, mdata

def state(h5group):
    return '\n'.join("{}: {}".format(k, v) for k, v in h5group.attrs.items())


@contextlib.contextmanager
def topen(root, date, n, mode='r'):
    """Load data from disk."""
    path = pjoin(root, "{date:%Y-%m-%d}", "telemetry_{n:04d}.hdf5").format(date=date, n=n)
    with h5py.File(path, mode) as f:
        t = f['telemetry']
        yield TelemetryContainer(t, n, date)
        
@contextlib.contextmanager
def tboth(root, date, ncl, nol, mode='r'):
    """Open both."""
    with topen(root, date, ncl, mode) as tcl:
        with topen(root, date, nol, mode) as tol:
            if tcl.group['slopes'].attrs.get("LOOPSTATE","") not in ("Closing", 1):
                click.secho("Closed loop loopstate={0}".format(tcl.group['slopes'].attrs.get("LOOPSTATE","")), fg='yellow')
                if not click.confirm('Are you sure?'):
                    raise click.Abort()
            if tol.group['slopes'].attrs.get("LOOPSTATE","") not in ("Open", 0):
                click.secho("Open loop loopstate={0}".format(tol.group['slopes'].attrs.get("LOOPSTATE","")), fg='yellow')
                if not click.confirm('Are you sure?'):
                    raise click.Abort()
            yield (tcl, tol)

def figure_name(openloop, closedloop, kind=None, ext="png", date=None, key=None, index=None, path=None, **kwargs):
    """Construct a filename."""
    parts = ["{date:%Y-%m-%d}","C{closedloop.n:04d}","O{openloop.n:04d}"]
    if kind is not None:
        parts.append("{kind:s}")
    if date is None:
        date = closedloop.date
    if key is not None:
        parts += ["{key:s}"]
    if index is not None:
        parts += ["{index:s}"]
    basename = "{0}.{{ext:s}}".format("-".join(parts))
    
    if path is None:
        path = pjoin("{date:%Y-%m-%d}", "C{closedloop.n:04d}-O{openloop.n:04d}")
        if kind is not None:
            path = pjoin(path, "{kind:s}")
        if subdir:
            path = pjoin(path, subdir)
    path = pjoin(path, basename)
    name = path.format(date=date, closedloop=closedloop, openloop=openloop, 
                       kind=kind, key=key, index=index_label(index), ext=ext)
    name = name.replace(":", "-")
    return name

def plot(key, extension="png", keyarg=False):
    """A plot function decorator"""
    def decorator(f):
        """A decorator for the plot function."""
        argspec = inspect.getargspec(f)
        defaults = dict(zip(argspec.args[-len(argspec.defaults):], argspec.defaults))
        default_kind = defaults.get('kind', None)
        
        @functools.wraps(f)
        def dotheplot(openloop, closedloop, **kwargs):
            date = kwargs.pop('date', closedloop.date)
            ext = kwargs.pop('extension', extension)
            kind = kwargs.setdefault('kind', default_kind)
            index = kwargs.get('index', None)
            subdir = kwargs.pop('subdir', False)
            path = kwargs.pop('path', None)
            with quantity_support():
                figure = f(openloop, closedloop, **kwargs)
                parts = ["{date:%Y-%m-%d}","C{closedloop.n:04d}","O{openloop.n:04d}","{kind:s}", "{key:s}", "{index:s}"]
                if keyarg:
                    parts.append(str(kwargs.get(keyarg, "")))
                basename = "{0}.{{ext:s}}".format("-".join(parts))
                
                if path is None:
                    path = pjoin("{date:%Y-%m-%d}", "C{closedloop.n:04d}-O{openloop.n:04d}", "{kind:s}")
                    if subdir:
                        path = pjoin(path, subdir)
                path = pjoin(path, basename)
                
                name = path.format(date=date, closedloop=closedloop, openloop=openloop, 
                                   kind=kind, key=key, index=index_label(index), ext=ext)
                name = name.replace(":", "-")
                
                if not os.path.isdir(os.path.dirname(name)):
                    os.makedirs(os.path.dirname(name))
                click.echo("--> Saving {0} for {1} to '{2}'".format(key, kind, name))
                figure.savefig(name)
                plt.close(figure)
        
        dotheplot.__wrapped__ = f
        return dotheplot
    return decorator
    
def generate_tiptilt(t):
    """Remove tiptilt."""
    ns = int(t.group['slopes'].attrs.get('WFSNS', 144))
    times, slopes = t['slopes']
    tip = slopes[:ns].mean(axis=0)
    tilt = slopes[ns:2*ns].mean(axis=0)
    return times, np.vstack((tip, tilt))
    
def remove_tiptilt(t):
    """Remove tiptilt from slopes, and return ttr slopes."""
    ns = int(t.group['slopes'].attrs.get('WFSNS', 144))
    times, slopes = t['slopes']
    times, tiptilt = t['tiptilt']
    txslopes = slopes[:ns] - tiptilt[None,0,:]
    tyslopes = slopes[ns:2*ns] - tiptilt[None,1,:]
    toslopes = slopes[2*ns:]
    return times, np.vstack((txslopes, tyslopes, toslopes))

def generate_pseudophase(t):
    """Extract pseudophase from an h5group"""
    ns = int(t.group['slopes'].attrs.get('WFSNS', 144)) * 2
    times, slopes = t['slopes']
    phase = np.dot(library['L'], slopes[:ns]).A.reshape((32,32,-1))
    return times, phase

def generate_tweeter_modes(t):
    """docstring for generate_tweeter_modes"""
    ns = int(t.group['slopes'].attrs.get('WFSNS', 144)) * 2
    times, slopes = t['slopes']
    modes = np.dot(library['H_d'], slopes[:ns]).A
    return times, modes

def generate_woofer_modes(t):
    """docstring for generate_tweeter_modes"""
    ns = int(t.group['slopes'].attrs.get('WFSNS', 144)) * 2
    times, slopes = t['slopes']
    modes = np.dot(library['Hw_d'], slopes[:ns]).A
    return times, modes

attributes_to_label = [
    ('g_t',"TWEETERGAIN", float),
    ('g_w',"WOOFERGAIN", float),
    ('c_t', "TWEETERBLEED", float),
    ('c_w', "WOOFERBLEED", float),
    (r'\alpha', 'ALPHA', float),
    ('r', "WFSCAMRATE", parse_rate)
]

def add_figlabel(fig, openloop, closedloop):
    """Add label to figure."""
    olfn = openloop.group.file.filename
    clfn = closedloop.group.file.filename
    if matplotlib.rcParams['text.usetex']:
        olfn = r'\verb+{}+'.format(olfn)
        clfn = r'\verb+{}+'.format(clfn)
    text = ["Closed: {}".format(clfn), "Open: {}".format(olfn)]
    try:
        g = closedloop.group['slopes']
        l = ", ".join("${}={}$".format(label, func(g.attrs.get(attr,"?"))) for label, attr, func in attributes_to_label)
        text.append(l)
    except KeyError:
        pass
    fig.text(0.01, 0.99, "\n".join(text), va='top', ha='left', fontsize='small')



def previous_noon(now=None):
    """Compute the previous noon for telemetry folders."""
    noon = dt.time(12, 0, 0)
    if now is None:
        now = dt.datetime.now()
    if now.hour >= 12:
        return dt.datetime.combine(now.date(), noon)
    else:
        yesterday = (now - dt.timedelta(days=1))
        return dt.datetime.combine(yesterday.date(), noon)
    
def parse_dt(value):
    """Return date"""
    if isinstance(value, dt.datetime):
        return previous_noon(value)
    return dt.datetime.strptime(value, "%Y-%m-%d").date()
    
def index_label(args):
    """Make an index label"""
    if args is None:
        return "mean"
    elif isinstance(args, slice):
        return "{0.start}:{0.stop}".format(args)
    else:
        return ",".join("{:02d}".format(int(a)) for a in args)
    

def generate_psds(source, rate, length=1024, **kwargs):
    """Generate PSDs"""
    from controltheory.fourier import frequencies
    from controltheory.periodogram import periodogram
    psd = periodogram(source, length=length, axis=source.ndim - 1, half_overlap=True, **kwargs)
    freq = frequencies(length, rate)
    return freq, psd
    
def mpv(array):
    """Minimum positive value."""
    return np.min(np.abs(array)[array != 0.0])
    
def collapse_psd(psd, kind, index=None, average=False):
    """Collapse a PSD"""
    if index is None:
        if 'pseudophase' == kind:
            psd_selected = (ap[...,None] * psd).sum(axis=tuple(range(psd.ndim - 1))) / ap.sum()
        else:
            psd_selected = psd.mean(axis=tuple(range(psd.ndim - 1)))
    elif isinstance(index, slice):
        psd_selected = np.moveaxis(psd[index], -1, 0).squeeze()
    else:
        index = tuple(index) + (slice(None, None),)
        psd_selected = np.moveaxis(psd[index], -1, 0).squeeze()
    
    if average and psd_selected.ndim > 1:
        psd_selected = psd_selected.mean(axis=tuple(range(1, psd_selected.ndim)))
    return psd_selected
    

@plot("Timeline", keyarg='short')
def plot_timeline(openloop, closedloop, kind='pseudophase', short=False):
    """Plot timeline of data from pseudophase and intensity."""
    gs = mgrid.GridSpec(2, 2, width_ratios=[1.0, 0.2], wspace=0.1)
    fig = plt.figure()
    ax_p = fig.add_subplot(gs[0,0])
    ax_i = fig.add_subplot(gs[1,0], sharex=ax_p)
    ax_hp = fig.add_subplot(gs[0,1], sharey=ax_p)
    ax_hi = fig.add_subplot(gs[1,1], sharey=ax_i)

    for ax in fig.axes:
        ax.ticklabel_format(style='plain')
    
    # Grab data
    ost, opp = openloop[kind]
    cst, cpp = closedloop[kind]
    
    
    add_figlabel(fig, openloop, closedloop)
    
    # Histogram
    _, bins, po = ax_hp.hist(np.median(opp, axis=-1).flatten(), 30, orientation='horizontal', alpha=0.5)
    ol_color = po[0].get_facecolor()
    _, bins, pc = ax_hp.hist(np.median(cpp, axis=-1).flatten(), bins, orientation='horizontal', alpha=0.5)
    cl_color = pc[0].get_facecolor()
    plt.setp(ax_hp.get_yticklabels(), visible=False)

    # Timelines
    if opp.ndim == 3:
        indexes = ((10,10), (20,10), (10, 20), (20, 20))
    else:
        indexes = [3, 5, 10, 20]
    
    for index in indexes:
        try:
            ax_p.plot(ost, opp[index], color=ol_color, alpha=0.5)
            ax_p.plot(cst, cpp[index], color=cl_color, alpha=0.5)
        except IndexError as e:
            pass
        
    ax_p.set_ylabel("{0}".format(kind.capitalize()))
    
    try:
        oit, ointen = openloop['intensity']
    except KeyError:
        ax_i.text(0.01, 0.01, "No open loop intensity data.", transform=ax_i.transAxes, va='bottom')
    else:
        _, bins, _ = ax_hi.hist(ointen.flatten(), 30, orientation='horizontal', alpha=0.5, normed=True)
        for s in [10, 20, 50]:
            oil, = ax_i.plot(oit, ointen[s], color=ol_color, alpha=0.1)
        ax_i.plot(oit, np.median(ointen, axis=0), label='Open Loop', color=ol_color)
    try:
        cit, cinten = closedloop['intensity']
    except KeyError:
        ax_i.text(0.01, 0.99, "No closed loop intensity data.", transform=ax_i.transAxes, va='top')
    else:
        _, bins, _ = ax_hi.hist(cinten.flatten(), bins, orientation='horizontal', alpha=0.5, normed=True)
        plt.setp(ax_hi.get_yticklabels(), visible=False)
        for s in [10, 20, 50]:
            cil, = ax_i.plot(cit, cinten[s], color=cl_color, alpha=0.1)
        ax_i.plot(cit, np.median(cinten, axis=0), label='Closed Loop', color=cl_color)
    ax_i.set_ylabel("Intensity (cts)")
    ax_i.set_xlabel("Time (s)")
    if short:
        midpoint = ((np.median(cst) + np.median(ost)) / 2.0).to(u.s).value
        ax_p.set_xlim(midpoint, midpoint + 1.0)
        
    if ax_i.lines:
        ax_i.legend()
    ax_hi.tick_params(bottom='off')
    return fig
    

@plot("2DView")
def plot_psuedophase_view(openloop, closedloop, kind='pseudophase'):
    """Plot 2d views."""
    gs = mgrid.GridSpec(2, 4, width_ratios=[1.0, 1.0, 1.0, 0.05], wspace=0.1)
    fig = plt.figure()
    
    ost, opp = openloop[kind]
    cst, cpp = closedloop[kind]
    # oit, ointen = openloop['intensity']
    # cit, cinten = closedloop['intensity']
    add_figlabel(fig, openloop, closedloop)
    
    pnorm = mnorm.Normalize()
    pos = 10, 100, min([int(0.9 * cst.shape[0]), int(0.9 * ost.shape[0])])
    pnorm.autoscale([ opp[...,t] for t in pos ] + [ cpp[...,t] for t in pos ])
    
    for i,t in enumerate(pos):
        ax_op = fig.add_subplot(gs[0, i])
        oim = ax_op.imshow(opp[...,t], norm=pnorm)
        ax_op.set_title("{0} at t={1:.2f}s".format(kind, ost[t]))
        ax_cp = fig.add_subplot(gs[1, i])
        cim = ax_cp.imshow(cpp[...,t], norm=pnorm)
        if i == 0:
            ax_op.set_ylabel("Open Loop")
            ax_cp.set_ylabel("Closed Loop")
    fig.colorbar(oim, cax=fig.add_subplot(gs[:, -1]))
    # fig.colorbar(cim, cax=fig.add_subplot(gs[1, -1]))
    return fig
    
    
@plot("PSD")
def plot_psd(openloop, closedloop, kind='pseudophase', index=None, show_open=True):
    """docstring for plot_psd"""
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    
    ax.grid(True)
    ax.set_xlabel("Freq (Hz)")
    ax.set_ylabel("Power")
    ax.set_title("PSD for {0}, {1}".format(kind, "[{0}]".format(index_label(index))))
    add_figlabel(fig, openloop, closedloop)
    
    key = '{0}-psd'.format(kind)
    for (freq, psd), label in zip((openloop[key], closedloop[key]),("Open Loop", "Closed Loop")):
        ax.plot(freq, collapse_psd(psd, kind, index), label=label)
    if not show_open:
        ax.lines[0].remove()
    ax.autoscale_view()
    ax.relim()
    ax.set_yscale('log')
    ax.set_xlim(mpv(freq), np.max(freq))
    ax.set_xscale('log')
    ax.legend()
    return fig
    
def compute_etf(openloop, closedloop, kind, index, **kwargs):
    """Compute the ETF"""
    key = '{0}-psd'.format(kind)
    cfreq, cpsd = closedloop[key]
    ofreq, opsd = openloop[key]
    if not np.allclose(cfreq.value, ofreq.value) and cfreq.unit == ofreq.unit:
        raise ValueError("Periodogram baselines don't match!")
    else:
        freq = cfreq
    
    cpsd = collapse_psd(cpsd, kind, index, **kwargs)
    opsd = collapse_psd(opsd, kind, index, **kwargs)
    etf = cpsd / opsd
    assert freq.shape[0] == etf.shape[0]
    return freq, etf
    
@plot("ETF")
def plot_etf(openloop, closedloop, kind='pseudophase', index=None, show_nominal=True, show_fit=True, show_pegged_fit=True, label=None, figure=None, average=True):
    """Plot the error transfer function."""
    fig = figure or plt.figure()
    ax = fig.add_subplot(1,1,1)
    
    ax.grid(True)
    ax.set_xlabel("Freq (Hz)")
    ax.set_ylabel("ETF")
    ax.set_title("ETF for {0}, {1}".format(kind, "[{0}]".format(index_label(index))))
    add_figlabel(fig, openloop, closedloop)
    
    freq, etf = compute_etf(openloop, closedloop, kind, index, average=True)
    ax.plot(freq, etf, label=(label or "Transfer Function"))
    
    rate = parse_rate(closedloop.group['slopes'].attrs.get("WFSCAMRATE", 1.0))
    gain = float(closedloop.group['slopes'].attrs.get("TWEETERGAIN", 0.0))
    bleed = float(closedloop.group['slopes'].attrs.get("TWEETERBLEED", 0.99))
    model = TransferFunction(tau=1.1/rate, gain=gain, rate=rate, ln_c=1, integrator=bleed)
    
    if show_nominal:
        ax.plot(freq, model(freq.to("Hz").value), label=r'Model ($g={0.gain.value:.2f}$, $c={0.integrator:.2f}$, $\tau={0.tau.value:.2g}$s)'.format(model), color='r')
    
    if show_fit:
        if etf.ndim > 1:
            etf_to_fit = etf.mean(axis=tuple(range(1, etf.ndim)))
        else:
            etf_to_fit = etf
        
        fit_model = apply_LevMarLSQFitter(model, freq, etf_to_fit)
        ax.plot(freq, fit_model(freq.to("Hz").value), label=r'Fit ($g={0.gain.value:.2f}$, $c={0.integrator:.2f}$, $\tau={0.tau.value:.2g}$s)'.format(fit_model), color='g')
        if show_pegged_fit:
            model.ln_c.fixed = True
            fit_pegged = apply_LevMarLSQFitter(model, freq, etf_to_fit)
            ax.plot(freq, fit_pegged(freq.to("Hz").value), label=r'Fit ($g={0.gain.value:.2f}$, $c={0.integrator:.2f}$, $\tau={0.tau.value:.2g}$s)'.format(fit_pegged), color='m')
            
        
        
        
    ax.set_yscale('log')
    ax.set_xlim(mpv(freq), np.max(freq))
    ax.set_xscale('log')
    ax.legend()
    return fig
    
@plot("LFP")
def plot_lfp(openloop, closedloop, kind='fmodes', index=None, limit=True, figure=None, **kwargs):
    """Plot low frequency power"""
    key = '{0}-psd'.format(kind)
    cfreq, cpsd = closedloop[key]
    ofreq, opsd = openloop[key]
    
    if not np.allclose(cfreq.value, ofreq.value) and cfreq.unit == ofreq.unit:
        raise ValueError("Periodogram baselines don't match!")
    else:
        freq = cfreq
    etf = cpsd / opsd
    
    fig = figure or plt.figure()
    add_figlabel(fig, openloop, closedloop)
    ax = fig.add_subplot(1,1,1)
    if limit:
        lf = np.sort(np.abs(freq))[freq.shape[0] // 30]
        lfp = etf[...,np.abs(freq) < lf].mean(axis=-1)
        ax.set_title("Low Frequency Power (Below {1:.2g}) for {0}".format(kind, lf))
    else:
        lfp = etf.mean(axis=-1)
        ax.set_title("Power for {0}".format(kind))
    
    if lfp.ndim == 2:
        im = ax.imshow(lfp, **kwargs)
        fig.colorbar(im)
    else:
        ax.plot(lfp, **kwargs)
        ax.set_xlabel("Mode Number")
    return fig

