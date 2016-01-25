# -*- coding: utf-8 -*-
"""
A single data set.
"""

import datetime
import os

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr

from astropy.io import fits
import h5py

from .base import Base, FileBase
from .. import makedirs

def _parse_values_from_header(filename):
    """Parse argument values from a header file."""
    args = {}
    header = fits.getheader(filename)
    
    _HEADER_VALUES = [
        ('RATE', 'rate', float),
        ('GAIN', 'gain', float),
        ('CENT', 'centroid', str),
        ('WOOFER_B', 'woofer_bleed', float),
        ('TWEETER_', 'tweeter_bleed', float),
        ('ALPHA', 'alpha', float),
        ('MODE', 'mode', str),
        ('LOOP', 'loop', str),
    ]
    
    for key, name, kind in _HEADER_VALUES:
        args[name] = kind(header[key])
    
    datestring = header['DATE'] + "T" + header['TIME']
    args['created'] = datetime.datetime.strptime(datestring, '%Y-%m-%dT%H%M%S')
    return args
    

class Telemetry(FileBase):
    """A telemetry-based file object"""
    __abstract__ = True
    
    @declared_attr
    def dataset_id(self):
        return Column(Integer, ForeignKey('dataset.id'))

class Slopes(Telemetry):
    """Slope telemetry."""
    
    dataset = relationship("Dataset", backref=backref('slopes', uselist=False), uselist=False)
    
    @classmethod
    def from_dataset(cls, dataset):
        """Create slopes item from dataset."""
        data = dataset.read()
        nacross = int(dataset.mode.split('x',1)[0])
        ns = { 16 : 144 }[nacross]
        slopes = data[:,0:ns]
        filename = os.path.join(os.path.dirname(dataset.filename), 'telemetry', 
            'telemetry_{0:04d}.hdf5'.format(dataset.sequence_number))
        
        makedirs(os.path.dirname(filename))
        
        obj = cls(filename = filename, dataset = dataset)
        if not os.path.exists(filename):
            obj.data = slopes
            obj.write()
        return obj
    
    def write(self):
        """Write the data to an HDF5 file."""
        with h5py.File(self.filename) as f:
            dset = f.require_dataset('slopes', shape=self.data.shape, dtype=self.data.dtype)
            dset[...] = self.data
        
    def read(self):
        """Read telemetry from an HDF5 file."""
        with h5py.File(self.filename) as f:
            self._data = f['slopes'][...]
        return self._data


class Dataset(FileBase):
    """A single dataset."""
    
    sequence_number = Column(Integer)
    sequence_id = Column(Integer, ForeignKey('sequence.id'))
    sequence = relationship("Sequence", backref='datasets')
    
    created = Column(DateTime)
    
    # ShaneAO Operational parameters
    valid = Column(Boolean) # A flag to mark a header as unreliable.
    
    rate = Column(Float)
    gain = Column(Float)
    
    centroid = Column(String)
    
    woofer_bleed = Column(Float)
    tweeter_bleed = Column(Float)
    
    alpha = Column(Float)
    mode = Column(String)
    loop = Column(String)
    
    def get_sequence_attributes(self):
        """Collect the attributes which we might use to check sequencing."""
        return { 'rate' : self.rate, 'gain' : self.gain, 'centroid' : self.centroid, 
            'woofer_bleed' : self.woofer_bleed, 'tweeter_bleed' : self.tweeter_bleed,
            'alpha' : self.alpha, 'mode' : self.mode, 'loop' : self.loop,
             'date' : self.created.date()}
        
    
    @classmethod
    def from_filename(cls, filename):
        """Given a file name, figure out what to initialize with."""
        args = {'filename' : filename}
        
        args['sequence_number'] = int(os.path.splitext(filename)[0][-4:])
        args.update(_parse_values_from_header(filename))
        return cls(**args)
    
    def read(self):
        """Read the data from the original file."""
        data = fits.getdata(self.filename)[1:]
        return data
        