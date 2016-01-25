# -*- coding: utf-8 -*-

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class Sequence(Base):
    """A sequence is a created grouping of telemetry sets which can be co-added."""
    
    def __getattr__(self, name):
        """Given an attribute name, if it is in the sequence hash, return it."""
        if not len(self.datasets):
            raise AttributeError("{!r} has no attribute {!s}".format(self, name))
        attrs = self.datasets[0].get_sequence_attributes()
        if name in attrs:
            return attrs[name]
        raise AttributeError("{!r} has no attribute {!s}".format(self, name))
        
    

