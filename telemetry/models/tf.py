# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-

import datetime
import os
import warnings

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref, object_session
from sqlalchemy.orm.collections import attribute_mapped_collection

import h5py
import numpy as np

from .base import Base
from .kinds import DerivedTelemetry
from ..algorithms.transfer.model import TransferFunction as TransferFunctionModel

import astropy.units as u
import numpy as np

__all__ = ['TransferFunctionPair', 'TransferFunction']

class TransferFunctionPair(Base):
    """A pair of transfer function items."""
    
    loop_open_id = Column(Integer, ForeignKey("dataset.id"))
    loop_open = relationship("Dataset", foreign_keys="TransferFunctionPair.loop_open_id")
    
    loop_closed_id = Column(Integer, ForeignKey("dataset.id"))
    loop_closed = relationship("Dataset", foreign_keys="TransferFunctionPair.loop_closed_id", backref='pairs')
    
    @property
    def expected(self):
        """Expected model"""
        return TransferFunctionModel.expected(self.loop_closed)
    

class TransferFunction(DerivedTelemetry):
    """A transfer function from a stack of periodograms."""
    
    __mapper_args__ = {
            'polymorphic_identity':'transferfunction',
        }
        
    
    @classmethod
    def from_telemetry_kind(cls, kind):
        """From the name of a telemetry kind."""
        return cls(name="{0} transferfunction".format(kind), h5path='transferfunction/{0}'.format(kind), _kind="transferfunction")
        
    def generate(self, dataset):
        """From a dataset, generate a pair."""
        if not len(dataset.pairs):
            return
        self.generate_from_pair(dataset.pairs[0])
        
    @property
    def periodogram(self):
        """Periodogram kind."""
        return "periodogram/{0}".format(self.kind)
        
    
    def generate_from_pair(self, pair):
        """Given a dataset, generate a periodogram."""
        ol_data = np.asarray(pair.loop_open.telemetry[self.periodogram].read())
        cl_data = np.asarray(pair.loop_closed.telemetry[self.periodogram].read())
        tf_data = cl_data / ol_data
        
        with pair.loop_closed.open() as g:
            g.create_dataset(self.h5path, data=tf_data)
            g.attrs['length'] = tf_data.shape[-1]
            
        
    


