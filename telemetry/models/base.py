# -*- coding: utf-8 -*-

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, String, DateTime, Integer
import h5py
import os
import numpy as np

__all__ = ['Base']

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
        attrs = dict(self.__dict__)
        include = set(column.name for column in self.__table__.columns).union(include).union(self.INCLUDE)
        remove = (set(attrs.keys()).difference(include)).union(exclude).union(self.EXCLUDE)
        for key in remove:
            del attrs[key]
        return attrs
    

