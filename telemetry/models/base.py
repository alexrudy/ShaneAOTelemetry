# -*- coding: utf-8 -*-

__all__ = ['Base']

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, String, DateTime, Integer
import h5py
import os
import numpy as np
from .. import makedirs

class Base(declarative_base()):
    """A generic base class for uniform handling of things like the primary key."""
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    
    id = Column(Integer, primary_key=True, doc="Primary key identifier for the database.")
    

class DataAttribute(object):
    """A descriptor for data attributes"""
    def __init__(self, name, metadata=None):
        super(DataAttribute, self).__init__()
        self.name = name
        self.metadata = metadata or {}
        self.attr = "_{0}".format(self.name)
        self._writer = None
        self._reader = None
        
    def __get__(self, obj, objtype=None):
        """Access the underlying..."""
        if obj is None:
            return self
        if not hasattr(obj, self.attr):
            obj.read()
        return getattr(obj, self.attr)
    
    def __set__(self, obj, value):
        setattr(obj, self.attr, np.asanyarray(value))
        
    def writer(self, func):
        """Set up a generator function."""
        self._writer = func
        return func
        
    def reader(self, func):
        """docstring for reader"""
        self._reader = func
        return func
        
    def read(self, obj, g):
        """Read from HDF5"""
        if self._reader is None:
            setattr(obj, self.attr, g[self.name][...])
        else:
            self._reader.__get__(obj)(g)
        
    def write(self, obj, g):
        """Write to HDF5"""
        if not hasattr(obj, self.attr):
            return
        if self._writer is None:
            data = getattr(obj, self.attr)
            dset = g.require_dataset(self.name, shape=data.shape, dtype=data.dtype)
            dset[...] = data
        else:
            self._writer.__get__(obj)(g)


class FileBase(Base):
    """A base class for items that have a filename."""
    
    __abstract__ = True
    __h5path__ = None
    
    filename = Column(String)
    created = Column(DateTime)
    
    @classmethod
    def _iter_data(cls):
        """Iterate over data attributes"""
        for item in dir(cls):
            obj = getattr(cls, item)
            if isinstance(obj, DataAttribute):
                yield obj
    
    def check(self):
        """Check if the data exists."""
        try:
            self.read()
        except Exception as e:
            return False
        else:
            return True
    
    def read(self):
        """Read in the data from a file."""
        with h5py.File(self.filename) as f:
            if self.__h5path__ is not None:
                g = f[self.__h5path__]
            else:
                g = f
            for d in self._iter_data():
                d.read(self, g)
    
    def write(self):
        """Write the data to a file"""
        makedirs(os.path.dirname(self.filename))
        
        with h5py.File(self.filename) as f:
            if self.__h5path__ is not None:
                try:
                    g = f.require_group(self.__h5path__)
                except:
                    del f[self.__h5path__]
                    g = f.require_group(self.__h5path__)
            else:
                g = f
            for d in self._iter_data():
                d.write(self, g)
        
    
    