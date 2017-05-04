#!/usr/bin/env python
# coding: utf-8

import click
import os
import h5py
from os.path import join as pjoin

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np
import astropy.units as u
import datetime as dt

from ql import configure, tboth, parse_rate, parse_dt, generate_fmodes, quantity_support
from ql import generate_psds, generate_pseudophase, generate_tweeter_modes, generate_woofer_modes, generate_tiptilt, remove_tiptilt
from ql import plot_timeline, plot_psuedophase_view, plot_psd, plot_etf, plot_lfp, figure_name, compute_etf

def get_directory():
    """Get directory."""
    pathroot = os.path.abspath(pjoin("woofer-alpha"))
    try:
        os.makedirs(pathroot)
    except (IOError, OSError) as e:
        pass
    return pathroot

@click.command()
@click.option("--root", default=os.path.sep + pjoin("Volumes","LaCie","Telemetry2","ShaneAO"))
@click.option("--date", default="2017-03-15", type=parse_dt, help="Telemetry folder date.")
def main(root, date):
    """Quick look telemetry tools.
    
    Provide the telemetry numbers to examine for closed loop and open loop.
    
    """
    configure()
    
    lowest, highest = 33, 55
    figure_tetf = plt.figure()
    figure_tlfp = plt.figure()
    figure_wetf = plt.figure()
    figure_wlfp = plt.figure()
    directory = get_directory()
    
    for ncl, nol in zip(range(lowest, highest, 2), range(lowest + 1, highest + 1, 2)):
        click.echo("Opening CL={0} OL={1}".format(ncl, nol))
        click.echo("From {0} on {1}".format(root, date))
        with tboth(root, date, ncl, nol) as (tcl, tol):
            alpha = float(tcl.group['slopes'].attrs['ALPHA'])
            click.echo("alpha={:.1f}".format(alpha))
            # Generate necessary items.
            for t in (tcl, tol):
                t.generate('tiptilt', generate_tiptilt)
                t['slopes'] = remove_tiptilt(t)
                t.generate('pseudophase', generate_pseudophase)
                t.generate('tweeter-modes', generate_tweeter_modes)
                t.generate('woofer-modes', generate_woofer_modes)
                generate_fmodes(t)
                
            
            # Generate PSDs
            for t in (tcl, tol):
                rate = parse_rate(t.group['slopes'].attrs.get("WFSCAMRATE", 1.0))
                t['tweeter-modes-psd'] = generate_psds(t['tweeter-modes'][1], rate, length=1024)
                t['woofer-modes-psd'] = generate_psds(t['woofer-modes'][1], rate, length=1024)
                t['tweeter-psd'] = generate_psds(t['tweeter'][1], rate, length=1024)
                t['pseudophase-psd'] = generate_psds(t['pseudophase'][1], rate, length=1024)
                t['fmodes-psd'] = generate_psds(t['fmodes'][1], rate, length=1024)
            
            click.echo("Plotting PSDs and ETFs")
            alpha = float(tcl.group['slopes'].attrs['ALPHA'])
            label = r"Data $\alpha={0:.1f}$".format(alpha)
            name = figure_name(tol, tcl, "joint", ext="png", path=directory, key="ETF")
            
            f_to_save, etf_to_save = compute_etf(tol, tcl, 'woofer-modes', None, average=True)
            name_no_ext, ext = os.path.splitext(name)
            with h5py.File(name_no_ext + ".hdf5", mode='a') as hfile:
                freq = hfile.require_dataset("frequency", shape=f_to_save.shape, dtype=f_to_save.dtype)
                freq[...] = f_to_save
                etf = hfile.require_dataset("etf", shape=etf_to_save.shape, dtype=etf_to_save.dtype)
                etf[...] = etf_to_save
            
            
            with quantity_support():
                plot_etf(tol, tcl, kind='tweeter-modes', index=slice(0, 10), label=label, show_fit=True, show_nominal=True, show_joint_fit=True, path=directory)
                joint_etf = plt.figure()
                plot_etf.__wrapped__(tol, tcl, kind='tweeter-modes', index=slice(0, 10), label="tweeter", show_fit=False, show_nominal=False, figure=joint_etf)
                plot_etf.__wrapped__(tol, tcl, kind='woofer-modes', index=None, label="woofer", show_fit=False, show_nominal=False, figure=joint_etf)
                joint_etf.savefig(name)
                
                plot_etf.__wrapped__(tol, tcl, kind='tweeter-modes', index=slice(0, 10), label=label, show_fit=False, show_nominal=False, figure=figure_tetf)
                plot_etf.__wrapped__(tol, tcl, kind='woofer-modes', index=None, label=label, show_fit=False, show_nominal=False, figure=figure_wetf)
                plot_lfp.__wrapped__(tol, tcl, kind='tweeter-modes', label=label, figure=figure_tlfp)
                plot_lfp.__wrapped__(tol, tcl, kind='woofer-modes', label=label, figure=figure_wlfp)
    
    figure_tlfp.axes[0].legend()
    figure_tlfp.savefig(pjoin(directory, "LFP-tweeter-modes-Alpha.png"))
    figure_tetf.savefig(pjoin(directory, "ETF-tweeter-modes-Alpha.png"))
    figure_wlfp.axes[0].legend()
    figure_wlfp.savefig(pjoin(directory, "LFP-woofer-modes-Alpha.png"))
    figure_wetf.savefig(pjoin(directory, "ETF-woofer-modes-Alpha.png"))


if __name__ == '__main__':
    main()

