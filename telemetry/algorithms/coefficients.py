# -*- coding: utf-8 -*-
"""
Coefficient reconstructor.
"""
import os, os.path
import numpy as np

from astropy.io import fits

root = os.path.expanduser("~/Development/ShWL/")
def find_file(filename):
    """docstring for find_file"""
    chocies = ['parameterFiles', 'dataFiles']
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

def get_L_matrix():
    """docstring for get_L_matrix"""
    filename = os.path.join(root, 'dataFiles', 'reconMatrix_16xreal', "L.fits")
    return np.asmatrix(fits.getdata(filename))