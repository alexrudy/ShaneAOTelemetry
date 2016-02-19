# -*- coding: utf-8 -*-

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base
from .data import _DatasetBase

class Sequence(_DatasetBase):
    """A sequence is a created grouping of telemetry sets which can be co-added."""
    
    pair_id = Column(Integer, ForeignKey('sequence.id'))
    pair = relationship("Sequence", remote_side='Sequence.id')
    
    date = Column(DateTime)
    number = Column(Integer)
    
    def matched_pair_attributes(self):
        """Find a good matched pair."""
        attrs = self.get_sequence_attributes()
        # Remove attributes which could be confused.
        del attrs['loop']
        del attrs['gain']
        return attrs
        
        