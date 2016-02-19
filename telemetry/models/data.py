# -*- coding: utf-8 -*-
"""
A single data set.
"""

import datetime
import os
import numpy as np

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr

from astropy.io import fits
import h5py

from .base import Base, FileBase, DataAttribute
from .. import makedirs
from ..algorithms.coefficients import get_cm_projector, get_L_matrix

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
        ('CONTROLM', 'control_matrix', str),
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
    
    __h5path__ = "slopes"
    dataset = relationship("Dataset", backref=backref('slopes', uselist=False), uselist=False)
    
    sx = DataAttribute("sx")
    sy = DataAttribute("sy")
    
    @classmethod
    def from_dataset(cls, dataset):
        """Create slopes item from dataset."""
        data = dataset.read()
        nacross = int(dataset.mode.split('x',1)[0])
        ns = { 16 : 144 }[nacross]
        sx = data[:,0:ns]
        sy = data[:,ns:ns*2]
        filename = os.path.join(os.path.dirname(dataset.filename), 'telemetry', 
            'telemetry_{0:04d}.hdf5'.format(dataset.sequence_number))
        
        makedirs(os.path.dirname(filename))
        
        obj = cls(filename = filename, dataset = dataset)
        obj.sx = sx
        obj.sy = sy
        obj.write()
        return obj
    
    

class SVCoefficients(Telemetry):
    
    __h5path__ = "svd"
    
    dataset = relationship("Dataset", backref=backref('svcoefficients', uselist=False), uselist=False)
    
    coefficients = DataAttribute("coefficients")
    
    @classmethod
    def from_dataset(cls, dataset):
        """Create slopes item from dataset."""
        
        filename = os.path.join(os.path.dirname(dataset.filename), 'telemetry', 
            'telemetry_{0:04d}.hdf5'.format(dataset.sequence_number))
        
        makedirs(os.path.dirname(filename))
        
        obj = cls(filename = filename, dataset = dataset)
        if obj.check():
            return obj
        
        data = dataset.read()
        nacross = int(dataset.mode.split('x',1)[0])
        ns = { 16 : 144 }[nacross]
        slopes = data[:,0:ns*2]
        
        
        slvec = np.matrix(slopes.T)
        slvec.shape = (slvec.shape[0], slvec.shape[1], 1)
        
        vm = get_cm_projector(dataset.control_matrix)
        coeffs = vm * slvec
        data = coeffs.view(np.ndarray).T
        

        obj.coefficients = data
        obj.write()
        return obj

class Coefficients(Telemetry):
    
    __h5path__ = "hybird"
    
    dataset = relationship("Dataset", backref=backref('coefficients', uselist=False), uselist=False)
    
    coefficients = DataAttribute("coefficients")
    
    @classmethod
    def from_dataset(cls, dataset):
        """Create slopes item from dataset."""
        
        filename = os.path.join(os.path.dirname(dataset.filename), 'telemetry', 
            'telemetry_{0:04d}.hdf5'.format(dataset.sequence_number))
        
        makedirs(os.path.dirname(filename))
        
        obj = cls(filename = filename, dataset = dataset)
        if obj.check():
            return obj
        
        data = dataset.read()
        nacross = int(dataset.mode.split('x',1)[0])
        ns = { 16 : 144 }[nacross]
        slopes = data[:,0:ns*2]
        
        
        slvec = np.matrix(slopes.T)
        slvec.shape = (slvec.shape[0], slvec.shape[1], 1)
        
        vm = get_L_matrix()
        coeffs = vm * slvec
        data = coeffs.view(np.ndarray).T
        
        obj.coefficients = data
        obj.write()
        return obj
    

class _DatasetBase(FileBase):
    """A base class to share columns between dataset and sequence."""
    __abstract__ = True
    
    rate = Column(Float)
    gain = Column(Float)
    
    centroid = Column(String)
    
    woofer_bleed = Column(Float)
    tweeter_bleed = Column(Float)
    
    alpha = Column(Float)
    mode = Column(String)
    loop = Column(String)
    control_matrix = Column(String)
    
    def get_sequence_attributes(self):
        """Collect the attributes which we might use to check sequencing."""
        return { 'rate' : self.rate, 'gain' : self.gain, 'centroid' : self.centroid, 
            'woofer_bleed' : self.woofer_bleed, 'tweeter_bleed' : self.tweeter_bleed,
            'alpha' : self.alpha, 'mode' : self.mode, 'loop' : self.loop, 'date': self.date}
    
class Dataset(_DatasetBase):
    """A single dataset."""
    
    sequence_number = Column(Integer)
    sequence_id = Column(Integer, ForeignKey('sequence.id'))
    sequence = relationship("Sequence", backref='datasets')
    created = Column(DateTime)
    
    # ShaneAO Operational parameters
    valid = Column(Boolean, default=True) # A flag to mark a header as unreliable.
    
    @property
    def date(self):
        """The date this was created."""
        return self.created.date()
    
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
        