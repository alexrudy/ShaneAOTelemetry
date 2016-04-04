# -*- coding: utf-8 -*-

import os

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship, object_session
from sqlalchemy.sql import func


from .base import Base
from .data import _DatasetBase

class Sequence(_DatasetBase):
    """A sequence is a created grouping of telemetry sets which can be co-added."""
    
    pair_id = Column(Integer, ForeignKey('sequence.id'))
    pair = relationship("Sequence", remote_side='Sequence.id')
    
    date = Column(DateTime)
    number = Column(Integer)
    
    def match_sequence(self):
        """Match this sequence to a nearby pair for OL/CL comparison."""
        #TODO: Add ability to select previous or next pair by priority.
        attrs = self.matched_pair_attributes()
        matchq = object_session(self).query(Sequence).filter_by(**attrs).filter(Sequence.id != self.id).filter(Sequence.loop != self.loop)
        matches = matchq.order_by(func.abs(Sequence.number - self.number)).all()
        if not len(matches):
            return None
        closest = min(abs(s.number - self.number) for s in matches)
        matches = filter(lambda s : abs(s.number - self.number) <= closest, matches)
        matches.sort(key=lambda m : abs(len(m.datasets) - len(self.datasets)))
        self.pair = matches[0]
        return self.pair
    
    def matched_pair_attributes(self):
        """Find a good matched pair."""
        attrs = self.get_sequence_attributes()
        # Remove attributes which could be confused.
        del attrs['loop']
        del attrs['gain']
        return attrs
        
    def sequence_numbers(self):
        """Return the sequence numbers."""
        return [ dataset.sequence_number for dataset in self.datasets ]
        
    @property
    def file_root(self):
        """File root is based on the first dataset."""
        return self.datasets[0].file_root
        
    @property
    def filename(self):
        return os.path.join(self.file_root, 'telemetry', 
                    'telemetry_s{0:04d}.hdf5'.format(self.id))