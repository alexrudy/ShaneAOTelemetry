# -*- coding: utf-8 -*-

import datetime
import warnings
from astropy.io import fits

__all__ = ['parse_values_from_header']
SHANEAO_HEADER_VALUES = [
    ('NAXIS1', 'n_elements', int),
    ('SYSTEM', 'system', str),
    ('HEARTBEA', 'tweeter_heartbeat', bool),
    ('RTC_STAT', 'recon_enable', bool),
    ('RATE', 'wfs_rate', float),
    ('GAIN', 'gain', float),
    ('CENT', 'wfs_centroid', str),
    ('WOOFER_B', 'woofer_bleed', float),
    ('TWEETER_', 'tweeter_bleed', float),
    ('ALPHA', 'alpha', float),
    ('MODE', 'mode', str),
    ('SUBSTATE', 'substate', str),
    ('LOOP', 'loop', str),
    ('CONTROLM', 'control_matrix', str),
    ('REFCENT_', 'reference_centroids', str),
    ('TTRATE', 'tt_rate', float),
    ('TTCENT', 'tt_centroid', str),
    ('WOOFER', 'woofer_enable', lambda s : s == "on"),
    ('MEMS', 'tweeter_enable', lambda s : s == "on"),
    ('MEMS_OK', 'tweeter_check', bool),
    ('CAMERA', 'wfs_camera_state', str),
    ('WRATE', 'woofer_rate', float),
    ('TTCAMERA', 'tt_camera_state', str),
    ('TT_RGAIN', 'tt_rgain', float),
    ('FROZEN', 'frozen', bool),
    ('OFFLOADI', 'offload_enable', bool),
    ('UPLINK_L', 'uplink_loop', str),
    ('UPLINK_A', 'uplink_angle', float),
    ('UPLINK_B', 'uplink_bleed', float),
    ('UPLINK_G', 'uplink_gain', float),
    ('UPLINK_E', 'uplink_enabled', bool),
    ('HYBRIDCM', 'hybrid_matrix', str),
    ("KALMAN_B", 'hybrid_bleed', float),
    ("CENTREG", "wfs_cent_reg", float),
]

def get_created_datetime(header):
    """docstring for get_created_datetime"""
    datestring = header['DATE'] + "T" + header['TIME']
    return datetime.datetime.strptime(datestring, '%Y-%m-%dT%H%M%S')

def parse_values_from_header(filename_or_header):
    """Parse argument values from a FITS Header."""
    args = {}
    header = filename_or_header if isinstance(filename_or_header, fits.Header) else fits.getheader(filename_or_header)
    
    for key, name, kind in SHANEAO_HEADER_VALUES:
        try:
            args[name] = kind(header[key])
        except ValueError:
            if header[key] != 'unknown':
                raise ValueError("Can't parse {0}={1!r} as {2}".format(key, header[key], kind.__name__))
        except KeyError:
            warnings.warn("Can't find key {0} in header".format(key, header))
    
    args['created'] = get_created_datetime(header)
    args['date'] = args['created'].date()
    
    # Get additional keyword values which might have been missed.
    for key in header.keys():
        c = header.comments[key]
        if len(c) and " " not in c:
            if c not in args:
                args[c] = header[key]
    
    return args
    
