# -*- coding: utf-8 -*-

import os
import contextlib

from sqlalchemy import inspect
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship, backref, object_session, validates
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.sql import func


from .base import Base
from ..topological import topological_sort

__all__ = ['Telemetry', 'TelemetryKind', 'TelemetryPrerequisite']

class Telemetry(Base):
    """An association object with methods for telemetry."""
    _telemetry_kind_id = Column(Integer, ForeignKey('telemetrykind.id'))
    kind = relationship("TelemetryKind")
    
    _dataset_id = Column(Integer, ForeignKey('dataset.id', ondelete='CASCADE'))
    dataset = relationship("Dataset", backref=backref("telemetry", cascade="all, delete-orphan",
        collection_class=attribute_mapped_collection('kind.h5path')))
    
    
    @contextlib.contextmanager
    def open(self):
        """Open the dataset, as a context manager."""
        with self.dataset.open() as g:
            try:
                yield g[self.kind.h5path]
            except KeyError as e:
                print("Error opening {0} from {1} in {2}".format(self.kind.h5path, g.name, repr(self.dataset)))
                print("File: {0}".format(self.dataset.filename))
                raise
            
    def read(self):
        """Read the dataset."""
        with self.open() as d:
            return self.kind.read(d)
            
    def remove(self):
        """Remove telemetry"""
        with self.dataset.open() as g:
            g.pop(self.kind.h5path, None)
        
    def __repr__(self):
        """A telemetry data item."""
        return "<{0}({1}) kind={2} h5path={3} from Dataset {4:d} on {5:%Y-%m-%d}>".format(self.__class__.__name__,
            self.kind.__class__.__name__, self.kind.kind, 
            "/".join([self.dataset.h5path,self.kind.h5path]),
            self.dataset.sequence, self.dataset.date)


class TelemetryKind(Base):
    """A dataset in an HDF5 file, representing a specific type of telemetry."""
    
    _kind = Column(String)
    name = Column(String)
    h5path = Column(String, unique=True)
    
    @property
    def prerequisites(self):
        """The list of prerequisites"""
        return [ p.prerequisite for p in self._prerequisite_edges ]
        
    @property
    def rprerequisites(self):
        """Recursive prerequisites, topologically sorted."""
        to_check = collections.deque([self])
        all_prereqs = {}
        while len(to_check):
            kind = to_check.popleft()
            all_prereqs[kind] = kind.prerequisites
            to_check.extend(kind.prerequisites)
        return list(topological_sort(all_prereqs.items()))
    
    __mapper_args__ = {
            'polymorphic_identity': 'base',
            'polymorphic_on':'_kind',
        }
    
    def __repr__(self):
        """Represent this object"""
        return "<{0} name={1} h5path={2}>".format(self.__class__.__name__, self.name, 
            self.h5path)
    
    def read(self, dataset):
        """Read from the HDF5 file."""
        return dataset[...]
    
    @property
    def kind(self):
        """Telemetry base kind."""
        return self.name
    
    def filter(self, query):
        """Apply necessary dataset filters."""
        return query
    
    def add_prerequisite(self, session, prerequisite):
        """Add a prerequistie."""
        if prerequisite not in self.prerequisites:
            tp = TelemetryPrerequisite(source=self, prerequisite=prerequisite)
            session.add(tp)
        
    
    @classmethod
    def require(cls, session, name, h5path=None):
        """Create a telemetry kind from a session"""
        if h5path is None:
            h5path = name
        kind = session.query(cls).filter(cls.name == name).one_or_none()
        if kind is None:
            kind = cls(name=name, h5path=h5path)
            session.add(kind)
        return kind
    
    @validates('h5path')
    def validate_name(self, key, value):
        """Validate name."""
        if self._kind is None or self._kind == "base":
            mapper = inspect(self).mapper
            if value in mapper.polymorphic_map:
                self._kind = value
            else:
                self._kind = 'base'
        return value
    

class TelemetryPrerequisite(Base):
    
    _source_id = Column(Integer, ForeignKey("telemetrykind.id"))
    source = relationship("TelemetryKind", primaryjoin=_source_id==TelemetryKind.id, backref='_prerequisite_edges')
    _prerequisite_id = Column(Integer, ForeignKey("telemetrykind.id"))
    prerequisite = relationship("TelemetryKind", primaryjoin=_prerequisite_id==TelemetryKind.id, backref="_source_edges")

