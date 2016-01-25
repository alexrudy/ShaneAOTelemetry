# -*- coding: utf-8 -*-

import datetime
import os

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref, object_session
from sqlalchemy.orm.collections import attribute_mapped_collection

import h5py
import numpy as np

from .base import Base, FileBase
from ..algorithms.periodogram import periodogram
from .. import makedirs

class _PeriodogramBase(FileBase):
    """A periodogram base."""
    __abstract__ = True
    
    length = Column(Integer)
    rate = Column(Float)
    kind = Column(String)
    
    created = Column(DateTime)

class Periodogram(_PeriodogramBase):
    """A database class to represent a computed periodogram."""
    
    dataset_id = Column(Integer, ForeignKey('dataset.id'))
    dataset = relationship("Dataset", backref='periodograms')
    
    @classmethod
    def from_dataset(cls, dataset, kind, length=None, **kwargs):
        """Create a peridogoram from an individual dataset."""
        tel = getattr(dataset, kind)
        telemetry = tel.read()
        if length is None:
            length = telemetry.shape[0]
        pgram = periodogram(telemetry, length, **kwargs)
        
        filename = os.path.join(os.path.dirname(dataset.filename), 'periodogram', 
            "Periodogram_{0:04d}.hdf5".format(dataset.sequence_number))
        makedirs(os.path.dirname(filename))
        with h5py.File(filename) as f:
            g = f.require_group("periodograms")
            dset = g.require_dataset(kind, shape=pgram.shape, dtype=pgram.dtype)
            dset[...] = pgram
            dset.attrs['rate'] = dataset.rate
            dset.attrs['datset'] = dataset.filename
            dset.attrs['source'] = tel.id

        return cls(dataset=dataset, length=length, rate=dataset.rate, filename=filename,
            created=datetime.datetime.now(), kind=kind)
        
    def read(self):
        """Read from data."""
        with h5py.File(self.filename) as f:
            return f['periodograms'][self.kind][...]


class PeriodogramStack(_PeriodogramBase):
    """A stack of periodograms"""
    
    sequence_id = Column(Integer, ForeignKey("sequence.id"))
    sequence = relationship("Sequence", backref=backref('periodograms', collection_class=attribute_mapped_collection('kind')))
    
    @classmethod
    def from_sequence(cls, sequence, kind, length, **kwargs):
        """Create a periodogram from a sequence."""
        
        session = object_session(sequence)
        periodogram_stack = []
        
        for dataset in sequence.datasets:
            if kind in dataset.periodograms and dataset.periodograms[kind].length == length:
                periodogram = dataset.periodograms[kind]
            else:
                periodogram = Periodogram.from_dataset(dataset, kind, length=length, **kwargs)
                session.add(periodogram)
            
            periodogram_stack.append(periodogram.read())
            
        periodogram_stack = np.array(periodogram_stack)
        periodogram_average = periodogram_stack.mean(axis=0)
        
        filename = os.path.join(os.path.dirname(dataset.filename), 'periodogram', 
            "Periodogram_s{0:04d}.hdf5".format(sequence.id))
        
        makedirs(os.path.dirname(filename))
        
        with h5py.File(filename) as f:
            g = f.require_group("periodograms")
            dset = g.require_dataset(kind, shape=periodogram_average.shape, dtype=periodogram_average.dtype)
            dset[...] = periodogram_average
            dset.attrs['rate'] = dataset.rate
            dset.attrs['sequence'] = sequence.id
        
        return cls(sequence = sequence, filename = filename, length=length, rate=sequence.rate, 
            created=datetime.datetime.now(), kind=kind)
    
    