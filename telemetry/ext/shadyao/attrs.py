# -*- coding: utf-8 -*-

import datetime
import warnings
from astropy.io import fits

__all__ = ['parse_values_from_header']
SHADYAO_HEADER_VALUES = [
    ('SYSTEM', 'system', str),
    
    ('WFSCAMRATE', 'wfs_rate', float),
    ('WFSCENTROID', 'wfs_centroid', str),
    ("WFSCENTREG", "wfs_cent_reg", float),
    ('WFSCAMSTATE', 'wfs_camera_state', str),
    
    ('TWEETERGAIN', 'tweeter_gain', float),
    ('TWEETERBLEED', 'tweeter_bleed', float),
    ('MEMSPOWER', 'tweeter_enable', lambda s : s.lower() == "on"),
    ("TWEETERLLIM", 'tweeter_lower_lim', float),
    ("TWEETERULIM", 'tweeter_upper_lim', float),
    ("TWEETERNA", 'tweeter_na', int),
    
    
    ('WOOFERGAIN', 'woofer_gain', float),
    ('WOOFERBLEED', 'woofer_bleed', float),
    ('WOOFERSTATE', 'woofer_enable', lambda s : s.lower() == "on"),
    ('WOOFERRATE', 'woofer_rate', float),
    
    ('MODE', 'mode', str),
    ('ALPHA', 'alpha', float),
    ('LOOPSTATE', 'loop', str),
    ('CONTROLMATRIX', 'control_matrix', str),
    ('HYBRIDMATRIX', 'hybrid_matrix', str),
    ('REFCENTS', 'reference_centroids', str),
    
    ('TTCAMRATE', 'tt_rate', float),
    ('TTCAMCENTROID', 'tt_centroid', str),
    ('TTCAMSTATE', 'tt_camera_state', str),
    
    
]

def get_created_datetime(attrs):
    """Parse a datetime"""
    return datetime.datetime.strptime(attrs['DATE'], '%Y-%m-%dT%H%M%S')

def parse_values_from_header(attrs):
    """Parse argument values from an HDF5 file attributes."""
    args = {}
    for key, name, kind in SHADYAO_HEADER_VALUES:
        try:
            args[name] = kind(attrs[key])
        except ValueError:
            if attrs[key] != 'unknown':
                raise ValueError("Can't parse {0}={1!r} as {2}".format(key, attrs[key], kind.__name__))
        except KeyError:
            warnings.warn("Can't find key {0} in attributes".format(key))
    
    args['created'] = get_created_datetime(attrs)
    args['date'] = args['created'].date()
    return args
    
