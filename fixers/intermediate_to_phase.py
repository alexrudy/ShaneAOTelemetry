#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os, glob
import h5py

def visitor(name, obj):
    """Visit all HDF5 datasets, and mark them as raw."""
    if not isinstance(obj, h5py.Dataset):
        return
    obj.attrs['raw'] = True

def main():
    """Argument parsing, etc."""
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    opt = parser.parse_args()
    for path in opt.paths:
        for filename in glob.iglob(os.path.join(path, "*.hdf5")):
            with h5py.File(filename) as f:
                f.visititems(visitor)

if __name__ == '__main__':
    main()