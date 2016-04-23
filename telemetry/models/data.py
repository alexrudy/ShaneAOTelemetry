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
from ..algorithms.coefficients import get_cm_projector, get_matrix

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
        ('SUBSTATE', 'substate', str),
        ('LOOP', 'loop', str),
        ('CONTROLM', 'control_matrix', str),
        ('REFCENT_', 'refcents', str),
        ('TTRATE', 'ttrate', float),
        ('TTCENT', 'ttcentroid', str),
        ('WOOFER', 'woofer_enable', lambda s : s == "on"),
        ('MEMS', 'tweeter_enable', lambda s : s == "on"),
        ('MEMS_OK', 'tweeter_check', bool),
        ('CAMERA', 'camera_state', str),
        ('WRATE', 'woofer_rate', float),
        ('TTCAMERA', 'ttcamera_state', str),
        ('TT_RGAIN', 'ttrgain', float),
        ('FROZEN', 'frozen', bool),
        ('OFFLOADI', 'offload_enable', bool),
        ('UPLINK_L', 'uplink_loop', str),
        ('UPLINK_A', 'uplink_angle', float),
        ('UPLINK_B', 'uplink_bleed', float),
        ('UPLINK_G', 'uplink_gain', float),
        ('UPLINK_E', 'uplink_enabled', bool)
    ]
    
    for key, name, kind in _HEADER_VALUES:
        try:
            args[name] = kind(header[key])
        except ValueError:
            if header[key] != 'unknown':
                print("Can't parse {0}={1!r} as {2}".format(key, header[key], kind.__name__))
    
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

class HCoefficients(Telemetry):
    
    __h5path__ = "hmatrix"
    
    dataset = relationship("Dataset", backref=backref('hcoefficients', uselist=False), uselist=False)
    
    hcoefficients = DataAttribute("hcoefficients")
    
    @classmethod
    def from_dataset(cls, dataset):
        """Create slopes item from dataset."""
        obj = cls(filename = dataset.processed_filename, dataset = dataset)
        if obj.check():
            return obj
        
        data = dataset.read()
        nacross = int(dataset.mode.split('x',1)[0])
        
        ns = { 16 : 144 }[nacross]
        slopes = data[:,0:ns*2]
        
        
        slvec = np.matrix(slopes.T)
        slvec.shape = (slvec.shape[0], slvec.shape[1], 1)
        
        vm = get_matrix("H_d")
        coeffs = vm * slvec
        data = coeffs.view(np.ndarray).T
        
        obj.hcoefficients = data
        obj.write()
        return obj
    

class Phase(Telemetry):
    
    __h5path__ = "phase"
    
    dataset = relationship("Dataset", backref=backref('phase', uselist=False), uselist=False)
    
    phase = DataAttribute("phase")
    
    @classmethod
    def from_dataset(cls, dataset):
        """Create slopes item from dataset."""
        obj = cls(filename = dataset.processed_filename, dataset = dataset)
        if obj.check():
            return obj
        
        data = dataset.read()
        if data.shape[-1] == 2402:
            phase = data[:,-1024:]
        else:
            raise ValueError("Telemetry {0} doesn't contain phase points.".format(dataset.sequence_number))
        
        obj.phase = phase
        obj.write()
        return obj
    
class PseudoPhase(Telemetry):
    
    __h5path__ = "pseudophase"
    
    dataset = relationship("Dataset", backref=backref('pseudophase', uselist=False), uselist=False)
    
    pseudophase = DataAttribute("pseudophase")
    
    @classmethod
    def from_dataset(cls, dataset):
        """Create pseudophase item from dataset."""
        obj = cls(filename = dataset.processed_filename, dataset = dataset)
        if obj.check():
            return obj
        
        data = dataset.read()
        nacross = int(dataset.mode.split('x',1)[0])
        ns = { 16 : 144 }[nacross]
        slopes = data[:,0:ns*2]
        
        slvec = np.matrix(slopes.T)
        slvec.shape = (slvec.shape[0], slvec.shape[1], 1)
        
        vm = get_matrix("L")
        coeffs = vm * slvec
        data = coeffs.view(np.ndarray).T
        
        obj.pseudophase = data
        obj.write()
        return obj
        
class PseudoPhaseNTT(Telemetry):
    
    __h5path__ = "pseudophasentt"
    
    dataset = relationship("Dataset", backref=backref('pseudophasentt', uselist=False), uselist=False)
    
    pseudophasentt = DataAttribute("pseudophasentt")
    
    @classmethod
    def from_dataset(cls, dataset):
        """Create pseudophase item from dataset."""
        obj = cls(filename = dataset.processed_filename, dataset = dataset)
        if obj.check():
            return obj
        
        data = dataset.read()
        nacross = int(dataset.mode.split('x',1)[0])
        ns = { 16 : 144 }[nacross]
        slopes = data[:,0:ns*2]
        
        xslopes = slopes[:,0:ns]
        xslopes -= xslopes.mean(axis=1)[:,None]
        slopes[:,0:ns] = xslopes
        yslopes = slopes[:,ns:2*ns]
        yslopes -= yslopes.mean(axis=1)[:,None]
        slopes[:,ns:2*ns] = yslopes
        
        slvec = np.matrix(slopes.T)
        slvec.shape = (slvec.shape[0], slvec.shape[1], 1)
        
        vm = get_matrix("L")
        coeffs = vm * slvec
        data = coeffs.view(np.ndarray).T
        
        obj.pseudophasentt = data
        obj.write()
        return obj
        
        
class Tweeter(Telemetry):
    
    __h5path__ = "mirrors"
    
    dataset = relationship("Dataset", backref=backref('tweeter', uselist=False), uselist=False)
    
    tweeter = DataAttribute("tweeter")
    
    @classmethod
    def from_dataset(cls, dataset):
        """Create tweeter item from dataset."""
        obj = cls(filename = dataset.processed_filename, dataset = dataset)
        if obj.check():
            return obj
        
        data = dataset.read()
        nacross = int(dataset.mode.split('x',1)[0])
        ns = { 16 : 144 }[nacross]
        
        start = ns * 2 + (2 if "LGS" in dataset.mode else 0)
        stop = start + 1024
        tweeter = data[:,start:stop]
        tweeter.shape = (-1, 32, 32)
        obj.tweeter = tweeter
        obj.write()
        return obj

class FourierCoefficients(Telemetry):
    """docstring for FourierCoefficients"""
    
    __h5path__ = "fourier"
    
    dataset = relationship("Dataset", backref=backref('fmodes', uselist=False), uselist=False)
    
    fcoefficients = DataAttribute("fcoefficients")
    
    @classmethod
    def from_dataset(cls, dataset):
        """Create slopes item from dataset."""
        obj = cls(filename = dataset.processed_filename, dataset = dataset)
        if obj.check():
            return obj
        
        data = dataset.read()
        nacross = int(dataset.mode.split('x',1)[0])
        ns = { 16 : 144 }[nacross]
        slopes = data[:,0:ns*2]
        
        
        slvec = np.matrix(slopes.T)
        slvec.shape = (slvec.shape[0], slvec.shape[1], 1)
        
        vm = get_matrix("N")
        coeffs = vm * slvec
        data = coeffs.view(np.ndarray).T
        
        obj.fcoefficients = data
        obj.write()
        return obj
    

class _DatasetBase(FileBase):
    """A base class to share columns between dataset and sequence."""
    __abstract__ = True
    
    mode = Column(String)
    substate = Column(String)
    
    rate = Column(Float)
    gain = Column(Float)
    camera_state = Column(String)
    
    alpha = Column(Float)
    loop = Column(String)
    control_matrix = Column(String)
    refcents = Column(String)
    frozen = Column(Boolean)
    
    tweeter_enable = Column(Boolean)
    tweeter_bleed = Column(Float)
    tweeter_check = Column(Boolean)
    
    woofer_rate = Column(Float)
    woofer_enable = Column(Boolean)
    woofer_bleed = Column(Float)
    offload_enable = Column(Boolean)
    
    centroid = Column(String)
    
    ttrgain = Column(Float)
    ttrate = Column(Float)
    ttcentroid = Column(String)
    ttcamera_state = Column(String)
    
    
    uplink_loop = Column(String)
    uplink_angle = Column(Float)
    uplink_bleed = Column(Float)
    uplink_gain = Column(Float)
    uplink_enabled = Column(Boolean)
    
    
    @property
    def file_root(self):
        """File path root."""
        return os.path.dirname(os.path.dirname(self.filename))
        
    @property
    def figure_path(self):
        """Figure root path."""
        return os.path.join(self.file_root, "figures")
    
    def get_sequence_attributes(self):
        """Collect the attributes which we might use to check sequencing."""
        return { 'rate' : self.rate, 'gain' : self.gain, 'centroid' : self.centroid, 
            'woofer_bleed' : self.woofer_bleed, 'tweeter_bleed' : self.tweeter_bleed,
            'alpha' : self.alpha, 'mode' : self.mode, 'loop' : self.loop, 'date': self.date, 
            'control_matrix' : self.control_matrix, 'refcents' : self.refcents}
    
    def __repr__(self):
        """Sensible representation."""
        return "<{0} from {date:%Y-%m-%d} mode={mode:s} loop={loop:s} gain={gain:.2f}>".format(self.__class__.__name__, **self.get_sequence_attributes())
    
    
class Dataset(_DatasetBase):
    """A single dataset."""
    
    sequence_number = Column(Integer)
    sequence_id = Column(Integer, ForeignKey('sequence.id'))
    sequence = relationship("Sequence", backref='datasets')
    created = Column(DateTime)
    
    # ShaneAO Operational parameters
    valid = Column(Boolean, default=True) # A flag to mark a header as unreliable.
    
    @property
    def processed_filename(self):
        return os.path.join(self.file_root, 'telemetry', 
                    'telemetry_{0:04d}.hdf5'.format(self.sequence_number))
    
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
        