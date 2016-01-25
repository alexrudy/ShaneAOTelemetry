# -*- coding: utf-8 -*-

__all__ = ['Base']

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, String, DateTime, Integer

class Base(declarative_base()):
    """A generic base class for uniform handling of things like the primary key."""
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    
    id = Column(Integer, primary_key=True, doc="Primary key identifier for the database.")
    

class FileBase(Base):
    """A base class for items that have a filename."""
    
    __abstract__ = True
    
    filename = Column(String)
    created = Column(DateTime)
    
    _data = None
    
    @property
    def data(self):
        """Get the data associated with this object."""
        if self._data is None:
            self._data = self.read()
        return self._data
    
    @data.setter
    def data(self, value):
        """Data values."""
        self._data = value
    
    def read(self):
        """Read in the data from a file."""
        pass
    
    def write(self):
        """Write the data to a file"""
        pass
    
    