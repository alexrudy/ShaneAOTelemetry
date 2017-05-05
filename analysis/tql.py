#!/usr/bin/env python
# coding: utf-8

import click
import os
from os.path import join as pjoin

import matplotlib
matplotlib.use('Agg')

import numpy as np
import astropy.units as u
import datetime as dt

from ql import configure, tboth, parse_rate, parse_dt, generate_fmodes
from ql import generate_psds, generate_pseudophase, generate_tweeter_modes, generate_woofer_modes, generate_tiptilt, remove_tiptilt
from ql import plot_timeline, plot_psuedophase_view, plot_psd, plot_etf, plot_lfp

@click.command()
@click.option("--root", default=os.path.sep + pjoin("Volumes","LaCie","Telemetry2","ShaneAO"))
@click.option("--date", default=dt.datetime.now(), type=parse_dt, help="Telemetry folder date.")
@click.option("--outdir", default=os.getcwd(), type=click.Path(exists=True))
@click.argument("ncl", type=int)
@click.argument("nol", type=int)
def main(root, date, ncl, nol, outdir):
    """Quick look telemetry tools.
    
    Provide the telemetry numbers to examine for closed loop and open loop.
    
    """
    os.chdir(outdir)
    configure()
    with tboth(root, date, ncl, nol) as (tcl, tol):
        
        for t in (tcl, tol):
            t.generate('tiptilt', generate_tiptilt)
            t['slopes'] = remove_tiptilt(t)
            t.generate('pseudophase', generate_pseudophase)
            t.generate('tweeter-modes', generate_tweeter_modes)
            t.generate('woofer-modes', generate_woofer_modes)
        
        click.echo("Plotting timelines")
        for short in (True, False):
            plot_timeline(tol, tcl, date=date, short=short)
            plot_timeline(tol, tcl, kind='tweeter', date=date, short=short)
            plot_timeline(tol, tcl, kind='woofer', date=date, short=short)
            plot_timeline(tol, tcl, kind='tweeter-modes', date=date, short=short)
            plot_timeline(tol, tcl, kind='woofer-modes', date=date, short=short)
        
        if ("coefficients" in tcl.group) and ("coefficients" in tol.group):
            plot_timeline(tol, tcl, kind='coefficients', date=date)
        
        if ("icoefficients" in tcl.group) and ("icoefficients" in tol.group):
            plot_timeline(tol, tcl, kind='icoefficients', date=date)
        
        
        plot_psuedophase_view(tol, tcl, date=date)
        
        click.echo("Generating FModes")
        for t in (tcl, tol):
            generate_fmodes(t)
        
        click.echo("Generating PSDs")
        for t in (tcl, tol):
            rate = parse_rate(t.group['slopes'].attrs.get("WFSCAMRATE", 1.0))
            t['tweeter-modes-psd'] = generate_psds(t['tweeter-modes'][1], rate, length=1024)
            t['woofer-modes-psd'] = generate_psds(t['woofer-modes'][1], rate, length=1024)
            t['tweeter-psd'] = generate_psds(t['tweeter'][1], rate, length=1024)
            t['pseudophase-psd'] = generate_psds(t['pseudophase'][1], rate, length=1024)
            t['fmodes-psd'] = generate_psds(t['fmodes'][1], rate, length=1024)
        
        click.echo("Plotting PSDs and ETFs")
        
        plot_psd(tol, tcl, kind='tweeter-modes', index=None, date=date)
        plot_etf(tol, tcl, kind='tweeter-modes', index=None, date=date)
        plot_psd(tol, tcl, kind='tweeter-modes', index=slice(0,10), date=date)
        plot_etf(tol, tcl, kind='tweeter-modes', index=slice(0,10), date=date)
        plot_lfp(tol, tcl, kind='tweeter-modes', date=date)
        
        for i in range(50):
            plot_psd(tol, tcl, kind='tweeter-modes', index=(i,), date=date)
            plot_etf(tol, tcl, kind='tweeter-modes', index=(i,), date=date)
        
        plot_psd(tol, tcl, kind='woofer-modes', index=None, date=date)
        plot_etf(tol, tcl, kind='woofer-modes', index=None, date=date)
        plot_lfp(tol, tcl, kind='woofer-modes', date=date)
        for i in range(14):
            plot_psd(tol, tcl, kind='woofer-modes', index=(i,), date=date)
            plot_etf(tol, tcl, kind='woofer-modes', index=(i,), date=date)
        
        
        for index in [None, (10,10), (18,18)]:
            plot_psd(tol, tcl, kind='pseudophase', index=index, date=date)
            plot_psd(tol, tcl, kind='fmodes', index=index, date=date)
            plot_psd(tol, tcl, kind='tweeter', index=index, date=date, show_open=False)
            
            plot_etf(tol, tcl, kind='pseudophase', index=index, date=date)
            plot_etf(tol, tcl, kind='fmodes', index=index, date=date)
        
        for index in [(18,18), (16,19), (14,18), (13,16), (14,14), (16,13), (18,14), (19,16)]:
            plot_psd(tol, tcl, kind='fmodes', index=index, date=date)
            plot_etf(tol, tcl, kind='fmodes', index=index, date=date)
        
        plot_lfp(tol, tcl, date=date)
        plot_lfp(tol, tcl, limit=False, date=date)

if __name__ == '__main__':
    main()

