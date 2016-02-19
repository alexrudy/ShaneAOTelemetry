# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-

import datetime
import os

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref, object_session
from sqlalchemy.orm.collections import attribute_mapped_collection

import h5py
import numpy as np

from .base import Base, FileBase, DataAttribute
from .periodogram import FrequencyDomain

import astropy.units as u
import numpy as np

class TransferFunction(FileBase, FrequencyDomain):
    """A transfer function from a stack of periodograms."""
    __h5path__ = "transferfunction"
    created = Column(DateTime)
    
    
    sequence_id = Column(Integer, ForeignKey("sequence.id"))
    sequence = relationship("Sequence", backref=backref('transferfunctions', collection_class=attribute_mapped_collection('kind')))
    
    @classmethod
    def from_periodogram(cls, periodogram):
        """Create this object from a periodogram."""
        cl_data = periodogram.read()
        ol_data = periodogram.sequence.pair.periodograms[periodogram.kind].read()
        
        tf_data = cl_data / ol_data
        obj = cls(sequence = periodogram.sequence, length=periodogram.length, rate=periodogram.rate, filename=periodogram.filename,
         created=datetime.datetime.now(), kind=periodogram.kind)
        obj.data = tf_data
        obj.write()
        return obj
    

class TransferFunctionModel(FileBase, FrequencyDomain):
    """Transfer function model"""
    
    __h5path__ = "transferfunction"
    created = Column(DateTime)
    size = Column(Integer)
    
    sequence_id = Column(Integer, ForeignKey("sequence.id"))
    sequence = relationship("Sequence", backref=backref('transferfunctionmodels', collection_class=attribute_mapped_collection('kind')))
    
    tau = DataAttribute("tau")
    gain = DataAttribute("gain")
    integrator = DataAttribute("integrator")
    
    @classmethod
    def from_model(cls, tf, model):
        """docstring for from_model"""
        obj = cls(sequence = tf.sequence, length=tf.length, rate=tf.rate, filename=tf.filename,
                 created=datetime.datetime.now(), kind=tf.kind)
        obj.tau = model.tau.value
        obj.gain = model.gain.value
        obj.integrator = model.integrator.value
        obj.write()
        return obj
