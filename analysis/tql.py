#!/usr/bin/env python
# coding: utf-8

import click
import os
os.chdir(os.path.expanduser("~/Development/ShaneAO/ShWLSimulator"))
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
quantity_support()

import contextlib
import collections

from ShadyAO.config import ShadyConfigParser
from ShadyAO.tweeter import tweeter_aperture

from telemetry.ext.fourieranalysis.modeling.model import TransferFunction
from telemetry.ext.fourieranalysis.modeling.linfit import apply_LevMarLSQFitter


def configure():
    """Generate a configuration"""
    global cfg, ap, library
    cfg = ShadyConfigParser("ShadyAO.cfg")
    cfg.load_mode('16xsim')
    click.echo("Configuring ShadyAO in mode {0} from ShadyAO.cfg".format(cfg.get("reconstructor","mode")))
    ap = tweeter_aperture(cfg)
    
    # Show some information about this configuration.
    click.echo("Number of subapertures: {:d}".format(cfg.getint('WFS','ns')))
    click.echo("Size of full grid of phase data points: {0:d}x{0:d}".format(cfg.getint('reconstructor','ng')))
    click.echo("Number of tweeter actuators: {:d}".format(cfg.getint('tweeter','na')))
    
    # Load the ShadyAO matrix library.
    from ShadyAO.controlmatrix import MatrixLibrary
    library = MatrixLibrary(cfg)

class TelemetryContainer(collections.MutableMapping):
    """A telemetry container"""
    def __init__(self, group, n):
        super(TelemetryContainer, self).__init__()
        self.group = group
        self.n = n
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
        self._cache[key] = func(self.group)

def read(h5group):
    """Read a masked group"""
    mask = h5group['mask'][...] == 1
    assert mask.any(), "Some elements must be valid."
    axis = int(h5group['data'].attrs.get("TAXIS", 0))
    rate = float(h5group.attrs.get("WFSCAMRATE", 1.0))
    n = h5group['data'].shape[axis]
    times = np.linspace(0, n / rate, n)
    mtimes = np.compress(mask, times)
    mdata = np.compress(mask, h5group['data'], axis=axis)
    mdata = np.moveaxis(mdata, axis, -1)
    if h5group.name.endswith('tweeter'):
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
        yield TelemetryContainer(t, n)
        
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

def plot(key, extension="png"):
    """A plot function decorator"""
    def decorator(f):
        """A decorator for the plot function."""
        argspec = inspect.getargspec(f)
        defaults = dict(zip(argspec.args[-len(argspec.defaults):], argspec.defaults))
        default_kind = defaults.get('kind', None)
        @functools.wraps(f)
        def dotheplot(openloop, closedloop, **kwargs):
            date = kwargs.pop('date')
            ext = kwargs.pop('extension', extension)
            kind = kwargs.setdefault('kind', default_kind)
            index = kwargs.get('index', None)
            subdir = kwargs.pop('subdir', False)
            figure = f(openloop, closedloop, **kwargs)
            
            parts = ["{date:%Y-%m-%d}","C{closedloop.n:04d}","O{openloop.n:04d}","{kind:s}", "{key:s}", "{index:s}"]
            basename = "{0}.{{ext:s}}".format("-".join(parts))
            path = pjoin("{date:%Y-%m-%d}", "C{closedloop.n:04d}-O{openloop.n:04d}")
            if subdir:
                path = pjoin(path, subdir)
            path = pjoin(path, basename)
            
            name = path.format(date=date, closedloop=closedloop, openloop=openloop, 
                               kind=kind, key=key, index=index_label(index), ext=ext)
            if not os.path.isdir(os.path.dirname(name)):
                os.makedirs(os.path.dirname(name))
            click.echo("--> Saving {0} for {1} to '{2}'".format(key, kind, name))
            figure.savefig(name)
            plt.close(figure)
        return dotheplot
    return decorator

def generate_pseudophase(group):
    """Extract pseudophase from an h5group"""
    ns = int(group['slopes'].attrs.get('WFSNS', 144)) * 2
    times, slopes = read(group['slopes'])
    phase = np.dot(library['L'], slopes[:ns]).A.reshape((32,32,-1))
    return times, phase

attributes_to_label = [
    ('g_t',"TWEETERGAIN"),
    ('g_w',"WOOFERGAIN"),
    ('c_t', "TWEETERBLEED"),
    ('c_w', "WOOFERBLEED"),
    (r'\alpha', 'ALPHA'),
    ('r', "WFSCAMRATE")
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
        l = ", ".join("${}={}$".format(label, g.attrs.get(attr,"?")) for label, attr in attributes_to_label)
        text.append(l)
    except KeyError:
        pass
    fig.text(0.01, 0.99, "\n".join(text), va='top', ha='left', fontsize='small')

@plot("Timeline")
def plot_timeline(openloop, closedloop, kind='pseudophase'):
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
        ax_p.plot(ost, opp[index], color=ol_color, alpha=0.5)
        ax_p.plot(cst, cpp[index], color=cl_color, alpha=0.5)
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
    else:
        return "".join("{:02d}".format(int(a)) for a in args)
    
@click.command()
@click.option("--root", default=os.path.sep + pjoin("Volumes","LaCie","Telemetry2","ShaneAO"))
@click.option("--date", default=dt.datetime.now(), type=parse_dt, help="Telemetry folder date.")
@click.argument("ncl", type=int)
@click.argument("nol", type=int)
def main(root, date, ncl, nol):
    """Quick look telemetry tools.
    
    Provide the telemetry numbers to examine for closed loop and open loop.
    
    """
    configure()
    with tboth(root, date, ncl, nol) as (tcl, tol):
        tcl.generate('pseudophase', generate_pseudophase)
        tol.generate('pseudophase', generate_pseudophase)
        
        click.echo("Plotting timelines")
        plot_timeline(tol, tcl, date=date)
        plot_timeline(tol, tcl, kind='tweeter', date=date)
        plot_timeline(tol, tcl, kind='woofer', date=date)
        plot_psuedophase_view(tol, tcl, date=date)
        
        click.echo("Generating FModes")
        for t in (tcl, tol):
            time, phase = t['pseudophase']
            fmodes = np.fft.fftshift(np.fft.fftn(phase * ap[...,None], axes=(0,1)), axes=(0,1))
            t['fmodes'] = time, fmodes
        
        click.echo("Generating PSDs")
        for t in (tcl, tol):
            rate = float(t.group['slopes'].attrs.get("WFSCAMRATE", 1.0))
            t['tweeter-psd'] = generate_psds(t['tweeter'][1], rate, length=1024)
            t['pseudophase-psd'] = generate_psds(t['pseudophase'][1], rate, length=1024)
            t['fmodes-psd'] = generate_psds(t['fmodes'][1], rate, length=1024)
        
        click.echo("Plotting PSDs and ETFs")
        
        for index in [None, (10,10), (18,18)]:
            plot_psd(tol, tcl, kind='pseudophase', index=index, date=date)
            plot_psd(tol, tcl, kind='fmodes', index=index, date=date)
            plot_psd(tol, tcl, kind='tweeter', index=index, date=date)
            
            plot_etf(tol, tcl, kind='pseudophase', index=index, date=date)
            plot_etf(tol, tcl, kind='fmodes', index=index, date=date)
            plot_etf(tol, tcl, kind='tweeter', index=index, date=date)
        
        for index in [(18,18), (16,19), (14,18), (13,16), (14,14), (16,13), (18,14), (19,16)]:
            plot_psd(tol, tcl, kind='fmodes', index=index, date=date)
            plot_etf(tol, tcl, kind='fmodes', index=index, date=date)
        
        plot_lfp(tol, tcl, date=date)
        
        plot_lfp(tol, tcl, limit=False, date=date)

def generate_psds(source, rate, length=1024):
    """Generate PSDs"""
    from controltheory.fourier import frequencies
    from controltheory.periodogram import periodogram
    psd = periodogram(source, length=length, axis=source.ndim - 1, half_overlap=True)
    freq = frequencies(length, rate)
    return freq, psd
    
def mpv(array):
    """Minimum positive value."""
    return np.min(np.abs(array)[array != 0.0])
    
def collapse_psd(psd, kind, index=None):
    """Collapse a PSD"""
    if index is None:
        if 'pseudophase' == kind:
            psd_selected = (ap[...,None] * psd).sum(axis=tuple(range(psd.ndim - 1))) / ap.sum()
        else:
            psd_selected = psd.mean(axis=tuple(range(psd.ndim - 1)))
    else:
        index = tuple(index) + (None,)
        psd_selected = psd[index].squeeze()
    return psd_selected
    
@plot("PSD")
def plot_psd(openloop, closedloop, kind='pseudophase', index=None):
    """docstring for plot_psd"""
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    
    ax.grid(True)
    ax.set_xlabel("Freq (Hz)")
    ax.set_ylabel("Power")
    ax.set_title("PSD for {0}, {1}".format(kind, "[{0}]".format(",".join(map(str, index))) if index is not None else "Averaged"))
    add_figlabel(fig, openloop, closedloop)
    
    key = '{0}-psd'.format(kind)
    for (freq, psd),label in zip((openloop[key], closedloop[key]),("Open Loop", "Closed Loop")):
        ax.plot(freq, collapse_psd(psd, kind, index), label=label)
    ax.set_yscale('log')
    ax.set_xlim(mpv(freq), np.max(freq))
    ax.set_xscale('log')
    ax.legend()
    return fig
    
def compute_etf(openloop, closedloop, kind, index):
    """Compute the ETF"""
    key = '{0}-psd'.format(kind)
    cfreq, cpsd = closedloop[key]
    ofreq, opsd = openloop[key]
    if not np.allclose(cfreq.value, ofreq.value) and cfreq.unit == ofreq.unit:
        raise ValueError("Periodogram baselines don't match!")
    else:
        freq = cfreq
    
    cpsd = collapse_psd(cpsd, kind, index)
    opsd = collapse_psd(opsd, kind, index)
    etf = cpsd / opsd
    return freq, etf
    
@plot("ETF")
def plot_etf(openloop, closedloop, kind='pseudophase', index=None):
    """Plot the error transfer function."""
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    
    ax.grid(True)
    ax.set_xlabel("Freq (Hz)")
    ax.set_ylabel("ETF")
    ax.set_title("ETF for {0}, {1}".format(kind, "[{0}]".format(",".join(map(str, index))) if index is not None else "Averaged"))
    add_figlabel(fig, openloop, closedloop)
    
    freq, etf = compute_etf(openloop, closedloop, kind, index)

    ax.plot(freq, etf, label="Transfer Function")
    
    rate = float(closedloop.group['slopes'].attrs.get("WFSCAMRATE", 1.0))
    gain = float(closedloop.group['slopes'].attrs.get("TWEETERGAIN", 0.0))
    bleed = float(closedloop.group['slopes'].attrs.get("TWEETERBLEED", 0.99))
    model = TransferFunction(tau=1.1/rate, gain=gain, rate=rate, ln_c=1, integrator=bleed)
    
    ax.plot(freq, model(freq.to("Hz").value), label=r'Model ($g={0.gain.value:.2f}$, $c={0.integrator:.2f}$, $\tau={0.tau.value:.2g}$s)'.format(model), color='r')
    
    fit_model = apply_LevMarLSQFitter(model, freq, etf)
    ax.plot(freq, fit_model(freq.to("Hz").value), label=r'Fit ($g={0.gain.value:.2f}$, $c={0.integrator:.2f}$, $\tau={0.tau.value:.2g}$s)'.format(fit_model), color='g')
    
    ax.set_yscale('log')
    ax.set_xlim(mpv(freq), np.max(freq))
    ax.set_xscale('log')
    ax.legend()
    return fig
    
@plot("LFP")
def plot_lfp(openloop, closedloop, kind='fmodes', index=None, limit=True):
    """Plot low frequency power"""
    key = '{0}-psd'.format(kind)
    cfreq, cpsd = closedloop[key]
    ofreq, opsd = openloop[key]
    if not np.allclose(cfreq.value, ofreq.value) and cfreq.unit == ofreq.unit:
        raise ValueError("Periodogram baselines don't match!")
    else:
        freq = cfreq
    etf = cpsd / opsd
    
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    if limit:
        lf = np.sort(np.abs(freq))[freq.shape[0] // 30]
        lfp = etf[...,np.abs(freq) < lf].mean(axis=-1)
        ax.set_title("Low Frequency Power (Below {1:.2g}) for {0}".format(kind, lf))
    else:
        lfp = etf.mean(axis=-1)
        ax.set_title("Power for {0}".format(kind))
    im = ax.imshow(lfp)
    fig.colorbar(im)
    return fig
    
def dead_code():
    # In[15]:

    ETF_mean = (CL_psd * ap[...,None]).mean(axis=(0,1)) / (OL_psd * ap[...,None]).mean(axis=(0,1))


    # In[16]:

    model = TransferFunction(tau=1.1/250.0, gain=CL['slopes'].attrs['TWEETERGAIN'], rate=250, ln_c=-1)
    model.integrator = 0.9
    fit_model = apply_LevMarLSQFitter(model, CL_freq, ETF_mean)


    # In[17]:

    print(fit_model.integrator)
    print(fit_model)
    print(fit_model.tau * fit_model.rate)


    # In[18]:

    plt.xlabel("Freq (Hz)")
    plt.ylabel("Error Transfer")
    plt.title("ETF for Pseudophase for averaged phase")
    plt.plot(CL_freq, ETF_mean, label='Error Transfer Function')
    plt.plot(CL_freq, model(CL_freq.to("Hz").value), label='Theory', color='r')
    plt.plot(CL_freq, fit_model(CL_freq.to("Hz").value), label='Model', color='g')
    plt.yscale('log')
    plt.xlim(0.1, np.max(OL_freq).value)
    plt.xscale('log')
    plt.legend();


    # In[19]:

    plt.xlabel("Freq (Hz)")
    plt.ylabel("Power")
    plt.title("PSD for Pseudophase at 12,12 (@250Hz)")
    plt.plot(CL_freq, CL_psd[12,12,:], label='Closed Loop')
    plt.plot(OL_freq, OL_psd[12,12,:], label='Open Loop')
    plt.yscale('log')
    plt.xlim(1, np.max(OL_freq).value)
    plt.legend()
    plt.xscale('log')
    plt.savefig("ILS_PSP_12x12_PSD.pdf")


    # In[20]:

    ETF_1212 = CL_psd[12,12,:] / OL_psd[12,12,:]


    # In[21]:

    # ap = tweeter_aperture(cfg)
    plt.xlabel("Freq (Hz)")
    plt.ylabel("Error Transfer")
    plt.title("Error Transfer Function for Pseudophase on Internal Light Source")
    plt.plot(CL_freq, ETF_1212, label='Data at (12,12)')
    plt.plot(CL_freq, model(CL_freq.value), label=r'Model ($g={0.gain.value:.2f}$, $c={0.integrator:.2f}$, $\tau={0.tau.value:.2g}$s)'.format(model), color='red')
    plt.plot(CL_freq, fit_model(CL_freq.value), label=r'Fit ($g={0.gain.value:.2f}$, $c={0.integrator:.2f}$, $\tau={0.tau.value:.2g}$s)'.format(fit_model), color='green')
    plt.legend(fontsize='small')
    plt.yscale('log')
    plt.xlim(0.1, np.max(OL_freq).value)
    plt.xscale('log')
    plt.grid(True)
    plt.savefig("ILS_PSP_1212_ETF.pdf")


    # ## Fourier Modes

    # In[22]:

    cfm = np.fft.fftshift(np.fft.fftn(cpp * ap[...,None], axes=(0,1)), axes=(0,1))
    cfp = periodogram(cfm, length=psd_length, axis=2, half_overlap=True)


    # In[23]:

    ofm = np.fft.fftshift(np.fft.fftn(opp * ap[...,None], axes=(0,1)), axes=(0,1))
    ofp = periodogram(ofm, length=psd_length, axis=2, half_overlap=True)


    # In[24]:

    ETF_small = cfp[18,18] / ofp[18,18]


    # In[25]:

    model = TransferFunction(tau=1.1/250.0, gain=CL['slopes'].attrs['TWEETERGAIN'], rate=250, ln_c=-1)
    model.integrator = 0.9
    fit_model = apply_LevMarLSQFitter(model, CL_freq, ETF_small)


    # In[26]:

    plt.xlabel("Freq (Hz)")
    plt.ylabel("Error Transfer")
    plt.title("ETF for Pseudophase for averaged phase")
    plt.plot(CL_freq, ETF_small, label='Error Transfer Function')
    plt.plot(CL_freq, model(CL_freq.to("Hz").value), label='Theory', color='r')
    plt.plot(CL_freq, fit_model(CL_freq.to("Hz").value), label='Model', color='g')
    plt.yscale('log')
    plt.xlim(0.1, np.max(OL_freq).value)
    plt.xscale('log')
    plt.legend();


    # In[27]:

    ETF_large = cfp[28,28] / ofp[28,28]


    # In[28]:

    model = TransferFunction(tau=1.1/250.0, gain=CL['slopes'].attrs['TWEETERGAIN'], rate=250, ln_c=-1)
    model.integrator = 0.9
    fit_model = apply_LevMarLSQFitter(model, CL_freq, ETF_large)


    # In[29]:

    plt.xlabel("Freq (Hz)")
    plt.ylabel("Error Transfer")
    plt.title("ETF for Pseudophase for averaged phase")
    plt.plot(CL_freq, ETF_large, label='Error Transfer Function')
    plt.plot(CL_freq, model(CL_freq.to("Hz").value), label='Theory', color='r')
    plt.plot(CL_freq, fit_model(CL_freq.to("Hz").value), label='Model', color='g')
    plt.yscale('log')
    plt.xlim(0.1, np.max(OL_freq).value)
    plt.xscale('log')
    plt.legend();


    # In[30]:

    ETF_large = cfp[3,28] / ofp[3,28]


    # In[31]:

    plt.xlabel("Freq (Hz)")
    plt.ylabel("Error Transfer")
    plt.title("ETF for Pseudophase for averaged phase")
    plt.plot(CL_freq, ETF_large, label='Error Transfer Function')
    plt.plot(CL_freq, model(CL_freq.to("Hz").value), label='Theory', color='r')
    plt.plot(CL_freq, fit_model(CL_freq.to("Hz").value), label='Model', color='g')
    plt.yscale('log')
    plt.xlim(0.1, np.max(OL_freq).value)
    plt.xscale('log')
    plt.legend();


    # In[32]:

    ETF = cfp / ofp


    # In[33]:

    plt.imshow(ETF[..., np.abs(CL_freq) < 2 * u.Hz].mean(axis=-1))
    plt.colorbar()


    # # MCMC Fitting

    # In[34]:

    import emcee, corner
    from telemetry.ext.fourieranalysis.modeling.model import TransferFunction
    from telemetry.ext.fourieranalysis.modeling.mcmc import gauss_freq_weighting, lnprob
    from tqdm import tqdm_notebook as tqdm


    # In[35]:

    model = TransferFunction(tau=1.1/250.0, gain=0.6, rate=250, ln_c=-1)
    model.integrator = 0.9


    # In[36]:

    start = model.parameters[:3]
    ndim = start.shape[0]
    nwalkers = 500
    pos = start[None,:] * np.random.randn(nwalkers,ndim) * 1e-3

    x = CL_freq.to('Hz').value
    w = gauss_freq_weighting(x)
    y = np.log(ETF_1212)
    nsteps = 1000
    sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob, args=(x, y, model.rate.value, w))
    for result in tqdm(sampler.sample(pos, iterations=nsteps), total=nsteps):
        pass


    # In[37]:

    plt.plot(sampler.chain[:,:,1].T, color='k');
    plt.ylabel(r"gain")
    plt.xlabel(r"Iteration")


    # In[ ]:

    samples = sampler.chain[:,150:,:].reshape((-1, ndim))


    # In[ ]:

    parameters = model.parameters[:3].copy()
    csamples = samples.copy()
    csamples[...,0] = np.log10(samples[..., 0] * model.rate)
    parameters[0] = np.log10(parameters[0] * model.rate)
    csamples[...,2] = 1.0 - np.exp(csamples[...,2])
    parameters[2] = 1.0 - np.exp(parameters[2])
    fig = corner.corner(csamples, labels=[r"$\log(\tau)$", "$gain$", "$c$"], truths=parameters, quantiles=[0.5], show_titles=True)


    # In[ ]:

    bgp = np.median(samples, axis=0)
    fit_model = TransferFunction(*bgp, rate=250)
    print(fit_model)


    # In[ ]:

    # ap = tweeter_aperture(cfg)
    plt.xlabel("Freq (Hz)")
    plt.ylabel("Error Transfer")
    plt.title("Error Transfer Function for Pseudophase on Internal Light Source")
    plt.plot(CL_freq, ETF_1212, label='Data at (12,12)')
    plt.plot(CL_freq, model(CL_freq.value), label=r'Model ($g={0.gain.value:.2f}$, $c={0.integrator:.2f}$, $\tau={0.tau.value:.2g}$s)'.format(model), color='red')
    plt.plot(CL_freq, fit_model(CL_freq.value), label=r'Fit ($g={0.gain.value:.2f}$, $c={0.integrator:.2f}$, $\tau={0.tau.value:.2g}$s)'.format(fit_model), color='green')
    plt.legend(fontsize='small')
    plt.yscale('log')
    plt.xlim(0.1, np.max(OL_freq).value)
    plt.xscale('log')
    plt.grid(True)
    plt.savefig("ILS_PSP_1212_ETF.pdf")


if __name__ == '__main__':
    main()

