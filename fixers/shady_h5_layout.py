#!/usr/bin/env python

import click
import h5py
import os
from os.path import join as pjoin
from glob import iglob

@click.command()
@click.argument("path", type=click.Path(exists=False))
@click.option("--simulator/--instrument", default=True, help="Is this the simulator?")
def main(path, simulator=True):
    """Fix HDF5 files."""
    if not path.endswith(".hdf5"):
        path = pjoin(path, "*.hdf5")
    click.echo(path)
    for filename in iglob(path):
        click.echo(filename)
        with h5py.File(filename, 'r+') as h5f:
            h5f.require_group("telemetry")
            click.echo(",".join(h5f.keys()))
            for key in h5f.keys():
                if key == 'telemetry':
                    continue
                click.echo("{0:s} -> {1:s}".format(key, 'telemetry/{0:s}'.format(key)))
                if simulator:
                    h5f[key].attrs['CMODE'] = "Simulator"
                else:
                    h5f[key].attrs['CMODE'] = "Real"
                h5f.move(key, 'telemetry/{0:s}'.format(key))
            click.echo(",".join(h5f.keys()))
            click.echo("telemetry/ ->" + ",".join(h5f['telemetry'].keys()))
            h5f.flush()
        
    

if __name__ == '__main__':
    main()