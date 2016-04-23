# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-

import datetime
import os
import warnings

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref, object_session
from sqlalchemy.orm.collections import attribute_mapped_collection

import h5py
import numpy as np

from .base import Base, FileBase, DataAttribute
from .periodogram import FrequencyDomain
from ..algorithms.transfer.model import TransferFunction as TFModel

import astropy.units as u
import numpy as np

class TransferFunction(FileBase, FrequencyDomain):
    """A transfer function from a stack of periodograms."""
    @property
    def __h5path__(self):
        """HDF5 path"""
        return "transferfunction/" + self.kind
    
    created = Column(DateTime)
    data = DataAttribute("data")
    
    sequence_id = Column(Integer, ForeignKey("sequence.id"))
    sequence = relationship("Sequence", backref=backref('transferfunctions', collection_class=attribute_mapped_collection('kind')))
    
    @classmethod
    def from_periodogram(cls, periodogram):
        """Create this object from a periodogram."""
        a_data = periodogram.read()
        b_data = periodogram.sequence.pair.periodograms[periodogram.kind].read()
        
        if periodogram.sequence.loop == "open":
            if periodogram.sequence.pair.loop != "closed":
                warnings.warn("Periodogram pair doesn't seem to match. {0:s}/{1:s}".format(periodogram.sequence.loop, periodogram.sequence.pair.loop))
            ol_data = a_data
            cl_data = b_data
        elif periodogram.sequence.loop == "closed":
            if periodogram.sequence.pair.loop != "open":
                warnings.warn("Periodogram pair doesn't seem to match. {0:s}/{1:s}".format(periodogram.sequence.loop, periodogram.sequence.pair.loop))
            ol_data = b_data
            cl_data = a_data
        
        tf_data = cl_data / ol_data
        obj = cls(sequence = periodogram.sequence, length=periodogram.length, rate=periodogram.rate, filename=periodogram.filename,
         created=datetime.datetime.now(), kind=periodogram.kind)
        obj.data = tf_data
        obj.write()
        return obj
    

class TransferFunctionModel(FileBase, FrequencyDomain):
    """Transfer function model"""
    
    @property
    def __h5path__(self):
        """HDF5 path"""
        return "transferfunction/models/" + self.kind
    
    created = Column(DateTime)
    size = Column(Integer)
    
    sequence_id = Column(Integer, ForeignKey("sequence.id"))
    sequence = relationship("Sequence", backref=backref('transferfunctionmodels', collection_class=attribute_mapped_collection('kind')))
    
    tau = DataAttribute("tau")
    gain = DataAttribute("gain")
    integrator = DataAttribute("integrator")
    
    def to_model(self, index=Ellipsis):
        """Return a model."""
        return TFModel(gain=self.gain[index], tau=self.tau[index], integrator=self.integrator[index], rate=self.rate)
    
    @classmethod
    def from_tf(cls, tf):
        """Make an emty model from a transfer function."""
        return cls(sequence = tf.sequence, length=tf.length, rate=tf.rate, filename=tf.filename,
                 created=datetime.datetime.now(), kind=tf.kind)
    
    def _update_h5path(self):
        """Update from the old path scheme."""
        with h5py.File(self.filename) as f:
            data_keys = ["tau", "gain", "integrator"]
            root = "transferfunction/" + self.kind
            if root in f:
                base_group = f[root]
                if "models" in base_group:
                    del base_group["models"]
                model_group = f.require_group("transferfunction/models/"+self.kind)
                if all(key in base_group for key in data_keys):
                    print("Updating model in HDF5 for {0}".format(self.filename))
                    for key in data_keys:
                        if key not in model_group:
                            f.move("{:s}/{:s}".format(root, key), "transferfunction/models/{:s}/{:s}".format(self.kind, key))
                        else:
                            del base_group[key]
                else:
                    print("Not all keys in {:s} in {:s}: {:s}".format(root, self.filename, ",".join(base_group.keys())))
            else:
                print("Apparently, no {:s} in {:s}".format(root, self.filename))
            
        
    def populate_from_model(self, model):
        """Set data from model"""
        self.tau = model.tau.value
        self.gain = model.gain.value
        self.integrator = model.integrator.value
    
    @classmethod
    def from_model(cls, tf, model):
        """docstring for from_model"""
        obj = cls.from_tf(tf)
        obj.populate_from_model(model)
        obj.write()
        return obj
