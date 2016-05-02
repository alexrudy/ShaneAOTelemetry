#!/usr/bin/env python
from __future__ import print_function
import sys, argparse, glob, os
import h5py
import six
import itertools
from celery import group

def main():
    """Main function for parsing."""
    from telemetry.application import app
    from telemetry.tasks import read
    from telemetry.cli import resultset_progress
    parser = argparse.ArgumentParser()
    default_path = os.path.join(app.config['TELEMETRY_ROOTDIRECTORY'], "**", "**", "raw")
    parser.add_argument("paths", nargs="*", help="Path names.", default=[default_path])
    parser.add_argument("-f", "--force", action='store_true', help="Force read all datasets.")
    opt = parser.parse_args()
    
    with app.app_context():
        
        paths = (os.path.expanduser(os.path.join(os.path.splitext(path)[0], '*.hdf5')) for path in opt.paths)
        paths = itertools.chain.from_iterable(glob.iglob(path) for path in paths)
        g = group(read.si(filename) for filename in paths)
        r = g.apply_async()
        resultset_progress(r)

if __name__ == '__main__':
    main()