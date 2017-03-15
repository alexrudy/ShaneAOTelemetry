#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
    
@click.command()
@click.option("--root", default=os.path.sep + pjoin("Volumes","LaCie","Telemetry2","ShaneAO"))
@click.option("--date", default=dt.datetime.now(), type=parse_dt, help="Telemetry folder date.")
@click.argument("n", type=int)
def main(root, date, n):
    """Quick look telemetry tools.
    
    Provide the telemetry numbers to examine for closed loop and open loop.
    
    """
    path = pjoin(root, "{date:%Y-%m-%d}", "telemetry_{n:04d}.hdf5").format(date=date, n=n)
    
    for fn in glob(path):
        try:
            click.echo("{0}".format(fn))
            with h5py.File(fn, 'r') as f:
                g = f['telemetry']['slopes']
                for key, value in sorted(g.attrs.items()):
                    click.echo("{0:s} = {1!r}".format(key, value))
        except (IOError, KeyError) as e:
            click.echo("Problem with {}: {!s}".format(fn, e))


if __name__ == '__main__':
    main()

