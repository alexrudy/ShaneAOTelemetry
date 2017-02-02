# -*- coding: utf-8 -*-

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import validates
from sqlalchemy import Column, Unicode, Integer, Boolean
import h5py
import os
import numpy as np

__all__ = ['Base', 'File']

class Base(declarative_base()):
    """A generic base class for uniform handling of things like the primary key."""
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    
    id = Column(Integer, primary_key=True, doc="Primary key identifier for the database.")
    
    INCLUDE = []
    EXCLUDE = []
    
    def attributes(self, include=set(), exclude=set()):
        """Return a dictionary of attributes."""
        attrs = {column.name:getattr(self,column.name) for column in self.__table__.columns}
        include = set(column.name for column in self.__table__.columns).union(include).union(self.INCLUDE)
        remove = (set(attrs.keys()).difference(include)).union(exclude).union(self.EXCLUDE)
        for key in remove:
            attrs.pop(key, None)
        return attrs
    
    def __repr__(self):
        """Default representation."""
        return "{0:s}({1:s})".format(
            self.__class__.__name__,
            ", ".join(["{0:s}={1!r}".format(k, v) for k, v in self.attributes().items() ]),
        )

class File(Base):
    """An object which represents a file on the disk."""
    
    __abstract__ = True
    
    filepath = Column(Unicode, doc="Path to the file.")
    exists = Column(Boolean, doc="Does the file exist on disk, as of last modification of this object.")
    
    @validates("filepath")
    def validate_filepath(self, key, path):
        """Validate a filepath, marking the exists property."""
        path = os.path.normpath(path)
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        self.exists = os.path.isfile(path)
        return path
    
    def validate(self):
        """Validate this object"""
        self.validate_filepath(self.filepath)
        
