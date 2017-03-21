# -*- coding: utf-8 -*-

import datetime
import warnings
import functools
from astropy.io import fits

__all__ = ['parse_values_from_header']

def translate_enum(enumeration, target_type=str):
    """Translate an enumeration"""
    
    def func(value):
        if isinstance(value, int):
            return enumeration[value]
        else:
            return target_type(value)
    return func

power = translate_enum({1 : True, 0: False}, lambda s : s.lower() in ("on", "enable", "enabled", "1"))
woofer = translate_enum({2: True, 1: False}, lambda s : s.lower() in ("on", "enable", "enabled", "1"))
rate_enumeration = {
    1: 50.0,
    2: 100.0,
    3: 250.0,
    4: 500.0,
    5: 700.0,
    6: 1000.0,
    7: 1300.0,
    8: 1500.0,
}
camera_rate = translate_enum(rate_enumeration, float)
loop = translate_enum({1:'Closed', 0:'Open'}, str)


SHADYAO_HEADER_VALUES = [
    ('SYSTEM', 'system', str),
    
    ('WFSCAMRATE', 'wfs_rate', camera_rate),
    ('WFSCENTROID', 'wfs_centroid', str),
    ("WFSCENTREG", "wfs_cent_reg", float),
    ('WFSCAMSTATE', 'wfs_camera_state', str),
    
    ('TWEETERGAIN', 'tweeter_gain', float),
    ('TWEETERBLEED', 'tweeter_bleed', float),
    ('MEMSPOWER', 'tweeter_enable', power),
    ("TWEETERLLIM", 'tweeter_lower_lim', float),
    ("TWEETERULIM", 'tweeter_upper_lim', float),
    ("TWEETERNA", 'tweeter_na', int),
    
    ('WOOFERGAIN', 'woofer_gain', float),
    ('WOOFERBLEED', 'woofer_bleed', float),
    ('WOOFERSTATE', 'woofer_enable', woofer),
    ('WOOFERRATE', 'woofer_rate', float),
    
    ('MODE', 'mode', str),
    ('ALPHA', 'alpha', float),
    ('LOOPSTATE', 'loop', loop),
    ('CONTROLMATRIX', 'control_matrix', str),
    ('HYBRIDMATRIX', 'hybrid_matrix', str),
    ('REFCENTS', 'reference_centroids', str),
    
    ('TTCAMRATE', 'tt_rate', camera_rate),
    ('TTCAMCENTROID', 'tt_centroid', str),
    ('TTCAMSTATE', 'tt_camera_state', str),
    
    
]

def get_created_datetime(attrs):
    """Parse a datetime"""
    return datetime.datetime.strptime(attrs['DATE'], '%Y-%m-%dT%H:%M:%S')

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
    try:
        args['created'] = get_created_datetime(attrs)
        args['date'] = args['created'].date()
    except KeyError:
        warnings.warn("Can't parse date from attrs")
    return args
    
