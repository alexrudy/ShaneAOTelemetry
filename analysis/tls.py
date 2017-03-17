#!/usr/bin/env python
# coding: utf-8

import click
import os
import h5py
from glob import iglob as glob
from os.path import join as pjoin
import datetime as dt
from astropy.table import Table
from telemetry.utils import parse_dt

def state(h5group):
    return '\n'.join("{}: {}".format(k, v) for k, v in h5group.attrs.items())

cam_enumeration = {0:0,1:50,2:100,3:250,4:500,5:700,6:1000,7:1300,8:1500}
def camera_rate_enumerator(enum):
    """Translate the camera rate enumerator"""
    if isinstance(enum, int):
        return float(cam_enumeration[enum])
    else:
        return float(enum)
    
loop_enumeration = {0:"Open",1:"Closed"}
def loop_enumerator(enum):
    """Translate the camera rate enumerator"""
    if isinstance(enum, int):
        return loop_enumeration[enum]
    else:
        return str(enum)

columns = [
    ("WFSCAMRATE", "WFS Rate", camera_rate_enumerator),
    ("LOOPSTATE", "Loop", loop_enumerator),
    ("TWEETERGAIN", "g_t", float),
    ("WOOFERGAIN", "g_w", float),
    ("TWEETERBLEED", "c_t", float),
    ("WOOFERBLEED", "c_w", float),
    ("ALPHA", "alpha", float),
    ("RECONSTRUCTOR", "recon", str),
]

@click.command()
@click.option("--root", default=os.path.sep + pjoin("Volumes","LaCie","Telemetry2","ShaneAO"))
@click.option("--date", default=dt.datetime.now(), type=parse_dt, help="Telemetry folder date.")
@click.option("--closed", default=False, is_flag=True, help="Only show closed loop data.")
def main(root, date, closed):
    """Quick look telemetry tools.
    
    Provide the telemetry numbers to examine for closed loop and open loop.
    
    """
    path = pjoin(root, "{date:%Y-%m-%d}", "telemetry_*.hdf5").format(date=date)
    click.echo("# Looking at telemetry at '{0}'".format(path))
    rows = []
    for fn in glob(path):
        try:
            with h5py.File(fn, 'r') as f:
                g = f['telemetry']['slopes']
                row = {'file' : os.path.basename(fn)}
                for attr, name, convert in columns:
                    row[name] = convert(g.attrs[attr])
                row['n'] = g['mask'][...].sum()
        except (IOError, KeyError) as e:
            click.echo("# Problem with {}: {!s}".format(fn, e))
        else:
            if (not closed) or (row['Loop'] == "Closed"): 
                rows.append(row)
    t = Table(rows, names=['file'] + ['n'] + [name for _, name, _ in columns])
    t.pprint(max_lines=-1)
    
    logfile = pjoin(root, "{date:%Y-%m-%d}", "telemetry.csv").format(date=date)
    t.write(logfile, format='ascii.ecsv')

if __name__ == '__main__':
    main()

