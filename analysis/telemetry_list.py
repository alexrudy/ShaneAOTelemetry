#!/usr/bin/env python
# coding: utf-8

import click
import os
import h5py
from glob import iglob as glob
from os.path import join as pjoin
import datetime as dt

def state(h5group):
    return '\n'.join("{}: {}".format(k, v) for k, v in h5group.attrs.items())

def parse_dt(value):
    """Return date"""
    return dt.datetime.strptime(value, "%Y-%m-%d").date()
    
@click.command()
@click.option("--root", default=os.path.sep + pjoin("Volumes","LaCie","Telemetry2","ShaneAO"))
@click.option("--date", default=dt.date.today(), type=parse_dt, help="Telemetry folder date.")
def main(root, date):
    """Quick look telemetry tools.
    
    Provide the telemetry numbers to examine for closed loop and open loop.
    
    """
    path = pjoin(root, "{date:%Y-%m-%d}", "telemetry_*.hdf5").format(date=date)
    
    for fn in glob(path):
        try:
            with h5py.File(fn, 'r') as f:
                g = f['telemetry']['slopes']
                click.echo("{} Rate: {} Loop: {:10s} TGain: {} WGain: {} TBleed: {} WBleed: {} Alpha: {} n={}".format(
                    os.path.basename(fn),
                    g.attrs['WFSCAMRATE'], g.attrs['LOOPSTATE'], 
                    g.attrs['TWEETERGAIN'], g.attrs['WOOFERGAIN'],
                    g.attrs['TWEETERBLEED'], g.attrs['WOOFERBLEED'],
                    g.attrs['ALPHA'],
                    g['mask'][...].sum(), 
                ))
        except (IOError, KeyError) as e:
            click.echo("Problem with {}: {!s}".format(fn, e))


if __name__ == '__main__':
    main()

