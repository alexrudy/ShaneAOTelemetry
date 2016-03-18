# -*- coding: utf-8 -*-
"""
Coefficient reconstructor.
"""
import os, os.path
import numpy as np

from astropy.io import fits

root = os.path.expanduser("~/Dropbox/Astronomy/LabFees/ShaneAO/")
def find_file(filename):
    """docstring for find_file"""
    chocies = ['parameters', 'data']
    for choice in chocies:
        path = os.path.join(root, choice, filename)
        if os.path.exists(path):
            return path
    else:
        raise ValueError("Can't locate '{0}'!".format(filename))

def get_cm_projector(matrix_filename):
    """Get the matrix to convert WFS measurements to coefficeints."""
    filename = find_file(matrix_filename)
    with fits.open(filename) as HDUs:
        cm = HDUs[0].data.copy()
        header = HDUs[0].header
    ntw = 1024
    ns = header['NS']
    nm = ns * 2
    
    # Crop out only slopes-to-tweeter.
    cm = cm[0:ntw,0:nm]
    
    u,s,v = np.linalg.svd(cm, full_matrices=False)
    # NOTE: only the first 182 of these appear to be restricted to inside the illuminated aperture
    vm = v[0:nm,:]
    return np.asmatrix(vm)

__cache = {}
def get_matrix(name, mode="16xreal"):
    """Get a matrix by name."""
    try:
        return __cache[(name, mode)]
    except KeyError:
        filename = find_file(os.path.join('reconMatrix_{0}'.format(mode), "{0}.fits".format(name)))
        with fits.open(filename) as HDUs:
            HDU = HDUs[0]
            if HDU.header.get("COMPLEX", False):
                # Work with a complex HDU.
                matrix = (HDU.data[0,...] + 1j * HDU.data[1,...]).astype(np.complex)
            else:
                matrix = HDU.data.astype(np.float)
        matrix = np.asmatrix(matrix)
        __cache[(name, mode)] = matrix
        return matrix
    