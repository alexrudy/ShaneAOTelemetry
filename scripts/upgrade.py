#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A script for updating ShaneAO unreal telemetry sequences to create
ShadyAO telemetry data sets.
"""

# Core imports.
import os, glob
import re
import collections
import itertools

# I/O
import h5py
from astropy.io import fits

# Data
import datetime
import time
import numpy as np
from astropy.time import Time

# Logging
import logging
import lumberjack

# CLI
import argparse
from astropy.utils.console import ProgressBar
import pstats
import cProfile

from telemetry.models.data import _parse_values_from_header

log = logging.getLogger("upgrade")

def sequence_attributes(header):
    """Given a header, return the relevant sequencing attributes."""
    return _parse_values_from_header(header)
    
class TelemetrySequence(object):
    """A sequence of identical telemetry dumps"""
    def __init__(self, attrs):
        super(TelemetrySequence, self).__init__()
        self.attrs = attrs # Telemetry attributes.
        self.sizes = get_data_sizes(attrs)
        self._filename = None
        self._file = None
        
    def __del__(self):
        """Delete the file, if necessary."""
        if self._file is not None:
            self._file.close()
        
    def compare(self, attrs):
        """Compare attributes."""
        this_attr = dict(self.attrs)
        this_attr.pop('created', None)
        
        other_attr = dict(attrs)
        other_attr.pop('created', None)
        success = this_attr == other_attr
        if not success:
            kdiff = set(this_attr.keys()) ^ set(other_attr.keys())
            if kdiff:
                log.debug("Different keys: {0}".format(", ".join(kdiff)))
            
            idiff = set(this_attr.items()) ^ set(other_attr.items())
            kdiff = set(k for k,v in idiff)
            log.debug("Different items: {0}".format(", ".join("{0}={1}->{2}".format(k,this_attr.get(k,'MISSING'),other_attr.get(k,'MISSING')) for k in kdiff)))
            
        return success
        
    @property
    def filename(self):
        """The HDF5 filename."""
        if self._filename is None:
            raise ValueError("File hasn't been set up yet!")
        return self._filename
        
    @filename.setter
    def filename(self, value):
        """Set the filename."""
        self._filename = str(value)
        
        
    def setup(self, n, root=".", mode="w"):
        """Set up the file."""
        self.filename = os.path.join(root,"telemetry_{0:04d}.hdf5".format(n))
        self._file = h5py.File(self.filename, mode)
        g = self._file.require_group("telemetry")
        g.attrs['unreal'] = np.array([0, 0])
        g.attrs['sequence'] = n
        self._setup_datasets(g)
        for k, v in self.attrs.items():
            if isinstance(v, (datetime.datetime,)):
                g.attrs[k] = time.mktime(v.timetuple())
            elif isinstance(v, (datetime.date,)):
                g.attrs[k] = v.toordinal()
            else:
                g.attrs[k] = v
        
    def _setup_datasets(self, g, nt=4096):
        """Set up h5py datasets."""
        for key, size in self.sizes.items():
            maxshape = [s or None for s in size] + [None]
            shape = size + (0,)
            chunks = size + (nt,)
            kwargs = {'shape':shape, 'maxshape':maxshape, 'dtype':np.float, 'chunks':chunks}
            if any(c == 0 for c in chunks):
                kwargs.pop('chunks')
            try:
                g.require_dataset(key, **kwargs)
            except TypeError:
                del g[key]
                g.create_dataset(key, **kwargs)
                
            
        
    
    def append_from_fits(self, filename):
        """Given a FITS filename, append."""
        basename = os.path.basename(filename)
        dnum = None
        m = re.match(r"Data_([\d]{4})\.fits", basename)
        if m:
            dnum = int(m.group(1))
        with fits.open(filename, memmap=False) as HDUs:
            self.append(HDUs[0].data.T[...,1:], dnum)
    
    def append(self, data, dnum=None):
        """Append a legacy dataset to this file."""
        g = self._file['telemetry']
        if dnum is not None:
            g.attrs['unreal'] = self._update_dnum_attr(g.attrs['unreal'], dnum)
        for key, data in self._split(data).items():
            self._append_dataset(g[key], data)
        self._file.flush()
            
        
    @staticmethod
    def _update_dnum_attr(dvalue, dnum):
        """Update the dataset number attribute."""
        dlow, dhigh = dvalue
        if dlow == 0 or dnum < dlow:
            dlow = dnum
        if dhigh == 0 or dnum > dhigh:
            dhigh = dnum
        return np.array([dlow, dhigh])
    
    @staticmethod
    def _append_dataset(d, data, axis=-1):
        """Append to an HDF5 dataset."""
        
        nt = data.shape[axis]
        
        # Compute resized shape.
        shape = list(d.shape)
        st = shape[axis]
        et = shape[axis] = st + nt
        d.resize(tuple(shape))
        sl = [slice(None, None) for s in shape]
        sl[axis] = slice(st, et)
        
        log.debug("{0} -> {1}".format(data.shape, d.chunks))
        # Write the data.
        d[tuple(sl)] = data[...]
            
    def _split(self, data):
        """Split a data array."""
        sdata = {}
        keys = "slopes tiptilt tweeter woofer filter uplink intermediate".split()
        start = 0
        end = 0
        for key in keys:
            if key in self.sizes:
                end += np.prod(self.sizes[key])
                if np.prod(self.sizes[key]):
                    d = data[start:end].reshape(self.sizes[key] + (-1,))
                else:
                    d = data[start:end]
                sdata[key] = d
                start += np.prod(self.sizes[key])
        # Special case sx & sy
        nx = np.prod(self.sizes['sx'])
        ny = np.prod(self.sizes['sy'])
        sdata['sx'] = data[0:nx]
        sdata['sy'] = data[nx:nx + ny]
        return sdata
    
def get_data_sizes(cseq):
    """Get data sizes."""
    na = int(cseq['n_elements'])
    
    sizes = collections.OrderedDict()
    if "16x" in cseq["mode"]:
        ns = 144
    sizes['slopes'] = (2 * ns,)
    sizes['tiptilt'] = (2,) if "LGS" in cseq["mode"] else (0,)
    sizes['tweeter'] = (32, 32)
    sizes['woofer'] = (52,)
    sizes['filter'] = (14,)
    sizes['uplink'] = (2,) if "LGS" in cseq["mode"] else (0,)
    
    na_simple = sum(np.prod(s) for s in sizes.values())
    if na_simple + 1024 == na:
        sizes['intermediate'] = (32, 32)
    
    sizes['sx'] = (ns,)
    sizes['sy'] = (ns,)
    
    return sizes

def main():
    """Main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str, help="Path to telemetry data.", nargs="+")
    parser.add_argument("-l", "--limit", type=int, help="Limit the number of files examined.")
    parser.add_argument("-p", "--profile", action='store_true', help="Use a profiler.")
    parser.add_argument("-v", "--verbose", action='store_true', help="Be verbose.")
    parser.add_argument("-f", "--force", action="store_true", help="Force write new files.")
    opt = parser.parse_args()
    
    if opt.profile:
        pr = cProfile.Profile()
        pr.enable()
    
    if opt.verbose:
        lumberjack.setup_logging(mode='stream', level=1)
    
    # Initial values for sequence attributes.
    cseq = {}
    cdata = []
    cnum = 0
    filedata = []
    filenames = itertools.chain.from_iterable(itertools.imap(glob.iglob,opt.path))
    if opt.limit is not None:
        filenames = itertools.islice(filenames, 0, opt.limit)
    
    for filename in filenames:
        attrs = sequence_attributes(filename)
        filedata.append((attrs['created'], filename, attrs))
    filedata.sort()
    
    print("Sequencing {:d} files.".format(len(filedata)))
    if not opt.verbose:
        fileiter = ProgressBar(filedata)
    fileiter = iter(fileiter)
    
    # Handle the first file.
    _, filename, attrs = next(fileiter)
    root = os.path.dirname(filename)
    sequence = TelemetrySequence(attrs)
    sequence.setup(cnum, root)
    sequence.append_from_fits(filename)
    
    for _, filename, attrs in fileiter:
        root = os.path.dirname(filename)
        if not sequence.compare(attrs):
            cnum += 1
            sequence = TelemetrySequence(attrs)
            sequence.setup(cnum, root, mode="w" if opt.force else "a")
            log.debug("New sequence '{0}'".format(sequence.filename))
        sequence.append_from_fits(filename)
    
    if opt.profile:
        pr.disable()
        sortby = 'cumulative'
        ps = pstats.Stats(pr).sort_stats(sortby)
        ps.print_stats()

if __name__ == '__main__':
    main()