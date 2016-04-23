#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A script for updating ShaneAO unreal telemetry sequences to create
ShadyAO telemetry data sets.
"""

import os, glob
import numpy as np
from astropy.io import fits
import h5py
import collections

SEQUENCE_ATTRS = [s.strip().split() for s in """
NAXIS1 n_telemetry
SYSTEM instrument_name
OFFLOADI offloat_enable
MEMS_OK tweeter_heartbeat
RATE wfs_rate
TT_RGAIN tt_rgain
WOOFER_B woofer_bleed
UPLINK_G uplink_gain
TTCAMERA tt_camstate
UPLINK_E uplink_enable
WRATE woofer_rate
CENT wfs_centroider
CAMERA wfs_camstate
UPLINK_A uplink_angle
UPLINK_B uplink_bleed
UPLINK_L uplink_loop
RTC_STAT recon_state
MEMS tweeter_state
ALPHA filter_alpha
WOOFER woofer_state
TWEETER_ tweeter_bleed
SUBSTATE substate
CONTROLM control_matrix
TTCENT tt_centroider
FROZEN frozen
REFCENT_ refcent_filename
MODE mode
GAIN gain
TTRATE tt_rate
HEARTBEA heartbeat
LOOP loop
WGAIN woofer_gain
""".splitlines()[1:-1]]

def sequence_attributes(header):
    """Given a header, return the relevant sequencing attributes."""
    return {name:header[key] for key, name in SEQUENCE_ATTRS}
    
def get_data_sizes(cseq):
    """Get data sizes."""
    KEYS = "sx sy slopes tweeter woofer uplink filter tiptilt".split()
    na = int(cseq['NAXIS1'])
    
    sizes = collections.OrderedDict((key,0) for key in KEYS)
    if "16x" in cseq["MODE"]:
        ns = 144
    sizes['sx'] = (ns,)
    sizes['sy'] = (ns,)
    sizes['slopes'] = (2 * ns,)
    sizes['tweeter'] = (32, 32)
    sizes['woofer'] = (52,)
    sizes['uplink'] = (2,) if "LGS" in cseq["MODE"] else (0,)
    sizes['filter'] = (14,)
    sizes['tiptilt'] = (2,) if "LGS" in cseq["MODE"] else (0,)
    return sizes
    
def split_data(cdata, sizes):
    """Given some sizes, split data."""
    sdata = {}
    keys = "slopes tiptilt tweeter woofer filter uplink".split()
    start = 0
    end = 0
    for key in keys:
        end += np.prod(sizes[key])
        sdata[key] = cdata[start:end].reshape(sizes[key] + (-1,))
        start += np.prod(sizes[key])
    nx = np.prod(sizes['sx'])
    ny = np.prod(sizes['sy'])
    sdata['sx'] = cdata[0:nx]
    sdata['sy'] = cdata[nx:nx + ny]
    return sdata
    
def write_sequence(cseq, cdata, cnum, root="."):
    """Write a sequence to disk."""
    filename = os.path.join(root,"telemetry_{0:04d}.hdf5".format(cnum))
    sizes = get_data_sizes(cseq)
    nt = sum(cd.shape[0] for cd in cdata)
    print("Creating telemetry file {0:s}".format(filename))
    with h5py.File(filename) as f:
        g = f.require_group("telemetry")
        for key, size in sizes.items():
            maxshape = [s or None for s in size] + [None]
            try:
                g.require_dataset(key, shape=size+(nt,), maxshape=tuple(maxshape), dtype=np.float, compression="gzip")
            except TypeError:
                del g[key]
                g.create_dataset(key, shape=size+(nt,), maxshape=tuple(maxshape), dtype=np.float, compression="gzip")
        et = 0
        for cd in cdata:
            st = et
            et += cd.shape[1]
            for key, data in split_data(cd, sizes).items():
                g[key][...,st:et] = data[...]
        for key, value in cseq.items():
            g.attrs[key] = value
    
def close_hdus(hdus_to_close):
    """Close open HDUs in a deque"""
    while len(hdus_to_close):
        hdus_to_close.pop().close()
    
def main():
    """Main function."""
    import argparse
    import itertools
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str, help="Path to telemetry data.", nargs="+")
    opt = parser.parse_args()
    
    # Initial values for sequence attributes.
    cseq = {}
    cdata = []
    cnum = 0
    hdus_to_close = collections.deque()
    
    try:
        for filename in itertools.chain.from_iterable(itertools.imap(glob.iglob,opt.path)):
            root = os.path.dirname(filename)
            HDUs = fits.open(filename, memmap=False)
            hdus_to_close.append(HDUs)
            seq = sequence_attributes(HDUs[0].header)
            if seq != cseq:
                if cseq:
                    # Only do the write not on the first file.
                    write_sequence(cseq, cdata, cnum, root)
                    cnum += 1
                cseq = seq
                cdata = [HDUs[0].data[1:]]
                close_hdus(hdus_to_close)
            else:
                cdata.append(HDUs[0].data)
        write_sequence(cseq, cdata, cnum, root)
    finally:
        close_hdus(hdus_to_close)

if __name__ == '__main__':
    main()