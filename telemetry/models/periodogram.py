# -*- coding: utf-8 -*-

import datetime
import os

from sqlalchemy.orm import validates
import h5py
import numpy as np

from .kinds import DerivedTelemetry
from ..algorithms.periodogram import periodogram

import astropy.units as u
import numpy as np

__all__ = ['Periodogram', 'frequencies']

def frequencies(length, rate):
    """docstring for frequencies"""
    rate = u.Quantity(rate, u.Hz)
    return (np.mgrid[-length//2:length//2].astype(np.float) / length) * rate

ATTRIBUTE_KEYS = "half_overlap suppress_static mean_remove skip_length start_length clip_length axis".split()


class Periodogram(DerivedTelemetry):
    """A periodogram object."""
    
    __mapper_args__ = {
            'polymorphic_identity':'periodogram',
        }
    
    H5PATH_ROOT = "periodogram"
    POLYMORPHIC_KIND = "periodogram"
    
    @classmethod
    def from_telemetry_kind(cls, kind):
        """From the name of a telemetry kind."""
        return cls(name="{0} periodogram".format(kind), h5path='periodogram/{0}'.format(kind), _kind="periodogram")
        
    def generate(self, dataset, length=1024, **kwargs):
        """Given a dataset, generate a periodogram."""
        data = np.asarray(dataset.telemetry[self.kind].read())
        pdata = periodogram(data.T, length, **kwargs).T
        if not np.isfinite(pdata).all():
            raise ValueError("Failed to periodogram {0} {1}".format(data.shape, repr(data)))
        with dataset.open() as g:
            g.create_dataset(self.h5path, data=pdata)
            g.attrs['length'] = length
            for key in ATTRIBUTE_KEYS:
                if key in kwargs:
                    g.attrs[key] = kwargs[key]
                
        
    

        