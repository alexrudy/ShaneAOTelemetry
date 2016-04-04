# -*- coding: utf-8 -*-

import datetime
import os

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref, object_session
from sqlalchemy.orm.collections import attribute_mapped_collection

import h5py
import numpy as np

from .base import Base, FileBase, DataAttribute
from ..algorithms.periodogram import periodogram

import astropy.units as u
import numpy as np

def frequencies(length, rate):
    """docstring for frequencies"""
    rate = u.Quantity(rate, u.Hz)
    return (np.mgrid[-length//2:length//2].astype(np.float) / length) * rate

KMAP = {
    'sx' : 'slopes',
    'sy' : 'slopes',
    'hcoefficients' : 'hcoefficients',
    'phase' : 'phase',
    'pseudophase' : 'pseudophase',
    'fmodes' : 'fmodes',
}

class FrequencyDomain(Base):
    """Things in the FrequencyDomain"""
    __abstract__ = True
    
    length = Column(Integer)
    rate = Column(Float)
    kind = Column(String)
    
    data = DataAttribute("data")
    
    
    @data.writer
    def _generate_data(self, g):
        """Generate the data group."""
        dset = g.require_dataset(self.kind, shape=self.data.shape, dtype=self.data.dtype)
        dset[...] = self.data
        dset.attrs['rate'] = self.rate
        dset.attrs['kind'] = self.kind
        
    @data.reader
    def _read_data(self, g):
        """Read the periodogram from a file."""
        self.data = g[self.kind][...]
        
    @property
    def frequencies(self):
        """Reuturn the frequencies"""
        return frequencies(self.length, self.rate)
    

class _PeriodogramBase(FileBase, FrequencyDomain):
    """A periodogram base."""
    __abstract__ = True
    __h5path__ = "periodograms"
    created = Column(DateTime)
    

class Periodogram(_PeriodogramBase):
    """A database class to represent a computed periodogram."""
    
    dataset_id = Column(Integer, ForeignKey('dataset.id'))
    dataset = relationship("Dataset", backref='periodograms')
    
    @classmethod
    def from_dataset(cls, dataset, kind, length=None, **kwargs):
        """Create a peridogoram from an individual dataset."""
        tel = getattr(dataset, KMAP.get(kind, kind))
        telemetry = getattr(tel, kind)
        if length is None:
            length = telemetry.shape[0]
        pgram = periodogram(telemetry, length, **kwargs)
        
        obj = cls(dataset=dataset, length=length, rate=dataset.rate, filename=dataset.processed_filename,
            created=datetime.datetime.now(), kind=kind)
        obj.data = pgram
        obj.write()
        return obj


class PeriodogramStack(_PeriodogramBase):
    """A stack of periodograms"""
    
    sequence_id = Column(Integer, ForeignKey("sequence.id"))
    sequence = relationship("Sequence", backref=backref('periodograms', collection_class=attribute_mapped_collection('kind')))
    
    def read(self):
        """Read from a file."""
        with h5py.File(self.filename) as f:
            self.data = f['periodograms'][self.kind][...]
        return self.data
    
    @classmethod
    def from_sequence(cls, sequence, kind, length, **kwargs):
        """Create a periodogram from a sequence."""
        obj = cls(sequence = sequence, filename=sequence.filename, length=length, rate=sequence.rate, 
            created=datetime.datetime.now(), kind=kind)
        
        if obj.check():
            return obj
        
        session = object_session(sequence)
        periodogram_stack = []
        
        for dataset in sequence.datasets:
            if kind in dataset.periodograms and dataset.periodograms[kind].length == length:
                periodogram = dataset.periodograms[kind]
            else:
                periodogram = Periodogram.from_dataset(dataset, kind, length=length, **kwargs)
                session.add(periodogram)
            
            periodogram_stack.append(periodogram.data)
            
        periodogram_stack = np.array(periodogram_stack)
        periodogram_average = periodogram_stack.mean(axis=0)
        
        obj.data = periodogram_average
        obj.write()
        return obj
    
    